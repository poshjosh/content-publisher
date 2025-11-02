import os
import logging

from typing import Dict, Any, Optional

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

from ..content_publisher import SocialContentPublisher, PostType, Content, PostResult, PostRequest
from .google_oauth import GoogleOAuth

logger = logging.getLogger(__name__)


class YouTubeContentPublisher(SocialContentPublisher):
    """Handler for YouTube API"""

    def __init__(self, api_endpoint: str, credentials: Dict[str, Any]):
        super().__init__([PostType.VIDEO, PostType.IMAGE, PostType.TEXT])
        self.__credentials = credentials
        self.__version = api_endpoint.split("/")[-1]
        self.service = None

    def authenticate(self, request: PostRequest):
        service_name = 'youtube'
        # Assuming credentials contain OAuth token or service account info
        if 'oauth_token' in self.__credentials:
            credentials = Credentials(token=self.__credentials['oauth_token'])
            self.service = build(service_name, self.__version, credentials=credentials)
        elif 'client_id' in self.__credentials and 'client_secret' in self.__credentials:
            oauth = GoogleOAuth({**self.__credentials, **request.post_config})
            # We need permission 'youtube.force-ssl' to upload subtitles
            scopes = oauth.to_scopes(['youtube', 'youtube.force-ssl'])
            credentials_filename = request.post_config.get("credentials_filename", "youtube.pickle")
            token_data = oauth.get_credentials_interactively(scopes, credentials_filename).data
            credentials = oauth.credentials_from_dict(token_data)
            self.service = build(service_name, self.__version, credentials=credentials)
        else:
            # Alternative: use API key for read-only operations
            self.service = build(service_name, self.__version, developerKey=self.__credentials.get('api_key'))

    def post_content(self, request: PostRequest, result: Optional[PostResult] = None) -> PostResult:
        """Post video content to YouTube"""
        if result is None:
            result = PostResult()
        try:

            content: Content = request.content

            if content.tags:
                if len(",".join([f'\"{e}\"' for e in content.tags if ' ' in e])) > 500:
                    return result.as_failure("Total length of tags exceeds maximum of 500 chars.")

            if not content.video_file:
                return result.as_failure("YouTube requires a video file")

            # https://developers.google.com/youtube/v3/docs/videos?hl=en#properties
            snippet = content.get_metadata('snippet', {
                # Note: 22=People & Blogs, 26=Howto & Style, 29=Nonprofits & Activism, 42=Shorts
                'categoryId': 26,
                'tags': content.tags if content.tags else ['trending'],
                'defaultLanguage': content.language_code if content.language_code else 'en',
                'defaultAudioLanguage': content.language_code if content.language_code else 'en'
            })
            max_len = 5000 - 50
            snippet.update({
                'title': self._truncate_with_ellipsis(content.title or content.description),
                'description': self._truncate_with_ellipsis(content.description, max_len),
            })
            status = content.get_metadata('status', {
                'privacyStatus': 'public',
                'selfDeclaredMadeForKids': False
            })

            body = {
                'snippet': snippet,
                'status': status
            }

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
            if image_file and PostType.IMAGE not in self.get_supported_post_types():
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
            if not subtitle_files:
                message = "Subtitles file(s) not provided"
                return result.add_step(message, logging.WARNING)

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