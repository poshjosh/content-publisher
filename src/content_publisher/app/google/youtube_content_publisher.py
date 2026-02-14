import os
import logging

from typing import Dict, Any, Optional

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

from ..content_publisher import SocialContentPublisher, PostType, Content, PostResult, PostRequest
from ..media import Media
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
        if 'oauth_token' in self.__credentials:
            credentials = Credentials(token=self.__credentials['oauth_token'])
            self.service = build(service_name, self.__version, credentials=credentials)
        elif 'client_id' in self.__credentials and 'client_secret' in self.__credentials:
            oauth = GoogleOAuth({**self.__credentials, **request.post_config})
            # We need permission 'youtube.force-ssl' to upload subtitles
            scopes = oauth.to_scopes(['youtube', 'youtube.force-ssl'])
            credentials_filename = request.get("credentials_filename", "youtube.pickle")
            credentials = oauth.get_credentials_interactively(scopes, credentials_filename)
            google_credentials = oauth.credentials_from_dict(credentials.data)
            self.service = build(service_name, self.__version, credentials=google_credentials)
        else:
            raise ValueError(f"Credentials insufficient for youtube authentication: {self.__credentials.keys()}")

    def validate_content(self, content: Content, result: Optional[PostResult] = None) -> PostResult:
        if result is None:
            result = PostResult()
        if not content.video_file:
            return result.as_failure("YouTube requires a video file")
        return super().validate_content(content, result)

    def post_content(self, request: PostRequest, result: Optional[PostResult] = None) -> PostResult:
        """Post video content to YouTube"""
        if result is None:
            result = PostResult()
        try:

            content: Content = request.content

            is_youtube_shorts = YouTubeContentPublisher.is_youtube_shorts(request)
            YouTubeContentPublisher.update_tags(content, is_youtube_shorts)

            # https://developers.google.com/youtube/v3/docs/videos?hl=en#properties
            snippet = content.get_metadata('snippet', {
                # Note: 22=People & Blogs, 26=Howto & Style, 29=Nonprofits & Activism, 42=Shorts
                # Using 42, caused problems
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

            response = self.upload_video(media, body, result)

            if not result.success:
                return result

            video_id = response['id']
            if is_youtube_shorts:
                result.post_url = f"https://www.youtube.com/shorts/{video_id}"
            else:
                result.post_url = f"https://www.youtube.com/watch?v={video_id}"
            result.platform_response = response

            if content.image_file and is_youtube_shorts is False and \
                    request.get('add_thumbnail', True) is True:
                result = self.add_thumbnail(content.image_file, video_id, result)

            playlist = request.get('playlist')
            if playlist:
                result = self.add_to_playlist(playlist, video_id, result)

            if content.subtitle_files and is_youtube_shorts is False and \
                    request.get('add_subtitles', True) is True:
                result = self.add_subtitles(content.subtitle_files, video_id, result)

            if not result.success:
                return result

            return result.as_success("Video posted successfully to YouTube")

        except Exception as ex:
            return result.as_failure_ex("Failed to post to YouTube", ex)

    @staticmethod
    def is_youtube_shorts(request: PostRequest) -> bool:
        is_portrait = request.get('media_orientation', None) == 'portrait'
        video_duration = Media.get_video_duration_seconds(request.content.video_file, 0.0)
        return is_portrait and 0.0 < video_duration < (180 - 5)

    @staticmethod
    def update_tags(content: Content, is_youtube_shorts: bool):
        shorts_tag = '#shorts'
        if is_youtube_shorts:
            if content.tags:
                if len([e for e in content.tags if shorts_tag in e.lower()]) == 0:
                    content.tags = [shorts_tag] + content.tags
            else:
                content.tags = [shorts_tag]

        tag_text_max_len = 500
        tag_text = ""
        tags = []
        for tag in content.tags:
            tag_text += f'\"{tag}\",' if ' ' in tag else f'{tag},'
            if len(tag_text) > tag_text_max_len:
                break
            tags.append(tag)

        content.tags = tags

    def upload_video(self, media: MediaFileUpload, body: Dict[str, Any], result: PostResult):
        try:
            insert_request = self.service.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )

            response = insert_request.execute()
            if response and 'id' in response:
                result.add_step(f"Video uploaded successfully - ID: {response['id']}")
            else:
                result.add_step(f"Failed to upload video to youtube, media: {media}"
                                f"\nResponse: {response}", logging.WARNING)
            return response
        except Exception as ex:
            message = f"Failed to upload video to youtube, media: {media}"
            logger.exception(message, exc_info=ex)
            result.add_step(message, logging.WARNING)
            return None

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

    def add_to_playlist(self, playlist_id: str, video_id: str, result: Optional[PostResult] = None) -> PostResult:
        """Add YouTube video to playlist"""
        if result is None:
            result = PostResult()
        try:
            if not playlist_id:
                message = f"Invalid playlist ID: {playlist_id}"
                return result.add_step(message, logging.WARNING)

            if not video_id:
                message = f"Invalid video ID: {video_id}"
                return result.add_step(message, logging.WARNING)

            insert_request = self.service.playlistItems().insert(
                part='snippet',
                body={
                    'snippet': {
                        'playlistId': playlist_id,
                        'resourceId': {
                            'kind': 'youtube#video',
                            'videoId': video_id
                        }
                    }
                }
            )

            insert_request.execute()
            result.add_step(f"Added video to playlist: {playlist_id}")

            return result
        except Exception as ex:
            message = f"Failed to add video to playlist: {playlist_id}, {str(ex)}"
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