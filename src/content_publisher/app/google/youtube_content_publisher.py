import os
import logging

from typing import Dict, Any, Optional

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

from ..content_publisher import SocialContentPublisher, PostType, Content, PostResult
from .google_oauth_token_generator import GoogleOAuthTokenGenerator

logger = logging.getLogger(__name__)


class YouTubeContentPublisher(SocialContentPublisher):
    """Handler for YouTube API"""

    def __init__(self, api_endpoint: str, credentials: Dict[str, Any]):
        super().__init__(api_endpoint, credentials, [PostType.VIDEO, PostType.IMAGE, PostType.TEXT])
        self.__version = api_endpoint.split("/")[-1]
        self.supports_subtitles = True
        self.service = None

    def _authenticate(self) -> bool:
        """Authenticate with YouTube API"""
        try:
            # Assuming credentials contain OAuth token or service account info
            if 'oauth_token' in self.credentials:
                creds = Credentials(token=self.credentials['oauth_token'])
                self.service = build('youtube', self.__version, credentials=creds)
            elif 'client_id' in self.credentials and 'client_secret' in self.credentials:
                creds_dict = self._get_youtube_credentials_interactively(self.credentials['client_id'], self.credentials['client_secret'])
                creds = Credentials(token=creds_dict['oauth_token'], refresh_token=creds_dict.get('refresh_token'))
                self.service = build('youtube', self.__version, credentials=creds)
            else:
                # Alternative: use API key for read-only operations
                self.service = build('youtube', self.__version, developerKey=self.credentials.get('api_key'))
            return True
        except Exception as ex:
            logger.error(f"YouTube authentication failed: {ex}")
            return False

    def post_content(self, content: Content, result: Optional[PostResult] = None) -> PostResult:
        """Post video content to YouTube"""
        if result is None:
            result = PostResult()
        try:
            if content.tags:
                if len(",".join([f'\"{e}\"' for e in content.tags if ' ' in e])) > 500:
                    return result.as_failure("Total length of tags exceeds maximum of 500 chars.")

            if not content.video_file:
                return result.as_failure("YouTube requires a video file")

            if not self._authenticate():
                return result.as_auth_failure()

            result.add_step("Authenticated with YouTube API")

            # Prepare video metadata
            # https://developers.google.com/youtube/v3/docs/videos?hl=en#properties
            body = {
                'snippet': {
                    'title': content.title or 'Untitled Video',
                    'description': content.description,
                    'categoryId': 22, # People & Blogs
                    'tags': ['trending']
                },
                'status': {
                    'privacyStatus': 'public',
                    'selfDeclaredMadeForKids': False
                }
            }

            if content.language_code:
                body['snippet']['defaultLanguage'] = content.language_code
                body['snippet']['defaultAudioLanguage'] = content.language_code

            if content.tags:
                body['snippet']['tags'] = content.tags

            # Create media upload object
            media = MediaFileUpload(
                content.video_file,
                chunksize=-1,
                resumable=True
            )

            result.add_step("Prepared video upload")

            # Upload video
            insert_request = self.service.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )

            response = insert_request.execute()
            video_id = response['id']

            result.add_step(f"Video uploaded successfully - ID: {video_id}")
            result.post_url = f"https://www.youtube.com/watch?v={video_id}"
            result.platform_response = response

            if content.image_file:
                self.add_thumbnail(content.image_file, video_id, result)

            # Add subtitles if provided
            if content.subtitle_files:
                self.add_subtitles(content.subtitle_files, video_id, result)

            if not result.success:
                return result

            return result.as_success("Video posted successfully to YouTube")

        except Exception as ex:
            return result.as_failure_ex("Failed to post to YouTube", ex)

    def add_thumbnail(self, image_file: str, video_id: str, result: Optional[PostResult] = None) -> PostResult:
        """Add thumbnail to YouTube video"""
        if result is None:
            result = PostResult()
        try:
            if image_file and PostType.IMAGE not in self.supported_post_types:
                return result.as_failure("Platform does not support image content")

            media = MediaFileUpload(image_file, chunksize=-1)

            set_request = self.service.thumbnails().set(
                videoId=video_id,
                media_body=media
            )

            set_request.execute()

            result.add_step(f"For video having ID: {video_id}, added thumbnail: {os.path.basename(image_file)}")

            return result
        except Exception as ex:
            message = f"Failed to add thumbnail: {str(ex)}"
            return result.as_failure(message)

    def add_subtitles(self, subtitle_files: Dict[str, str], video_id: str, result: Optional[PostResult] = None) -> PostResult:
        """Add subtitles to YouTube video"""
        if result is None:
            result = PostResult()
        try:
            if not self.supports_subtitles or not subtitle_files:
                message = "Adding of subtitles is not supported"
                return result.as_failure(message)

            for language, subtitle_file in subtitle_files.items():
                media = MediaFileUpload(subtitle_file, chunksize=-1)

                insert_request = self.service.captions().insert(
                    part='snippet',
                    body={
                        'snippet': {
                            'videoId': video_id,
                            'language': language,
                            'name': f'Subtitles ({language})',
                            'isDraft': False
                        }
                    },
                    media_body=media
                )

                insert_request.execute()
                result.add_step(f"Added subtitles for language: {language}")

            return result
        except Exception as ex:
            message = f"Failed to add subtitles: {str(ex)}"
            return result.as_failure(message)

    @staticmethod
    def _get_youtube_credentials_interactively(client_id: str, client_secret: str) -> Dict[str, str]:
        generator = GoogleOAuthTokenGenerator(client_id, client_secret)

        # We need permission 'youtube.force-ssl' to upload subtitles
        scopes = generator.to_scopes(['youtube', 'youtube.force-ssl'])
        tokens = generator.get_tokens_interactive(scopes, save_tokens=True)

        return {
            'oauth_token': tokens['access_token'],
            'refresh_token': tokens['refresh_token']
        }