import logging
import requests
from typing import Dict, Any, Optional

from ..content_publisher import SocialContentPublisher, PostType, Content, PostResult, PostRequest
from ..media import Media
from .tiktok_oauth import TikTokOAuth

logger = logging.getLogger(__name__)


class TikTokError(Exception):
    """Base exception for TikTok API error"""
    pass


class TikTokUploadError(TikTokError):
    """Exception raised for upload failures"""
    pass


class TikTokValidationError(TikTokError):
    """Exception raised for validation error"""
    pass


class TikTokContentPublisher(SocialContentPublisher):
    def __init__(self, api_endpoint: str, credentials: Dict[str, Any]):
        super().__init__([PostType.VIDEO, PostType.IMAGE, PostType.TEXT])
        self.__api_endpoint = api_endpoint.rstrip('/')
        self.__request_timeout = 30
        self.__credentials = credentials
        self.__access_token = None

    def authenticate(self, request: PostRequest):
        scopes = request.get("credentials_scopes",
                             ["user.info.basic", "video.upload", "video.publish"])
        filename = request.get("credentials_filename", "tiktok.pickle")
        oauth = TikTokOAuth(self.__api_endpoint, {**self.__credentials, **request.post_config})
        self.__access_token = oauth.get_credentials_interactively(scopes, filename).access_token

    def post_content(self, request: PostRequest, result: Optional[PostResult] = None) -> PostResult:
        """
        Post content to TikTok

        Args:
            request: PostRequest containing the Content object with video/image and metadata
            result: Optional PostResult object to track progress

        Returns:
            PostResult containing the post URL or error information

        Raises:
            TikTokValidationError: If content or other validation fails
            TikTokUploadError: If upload fails
        """

        if result is None:
            result = PostResult()

        try:

            content: Content = request.content

            init_response = self._initialize_upload(content)
            upload_url = init_response.get('upload_url')
            upload_id = init_response.get('upload_id')

            if not upload_url or not upload_id:
                result.as_failure("Invalid upload initialization response")

            response = self._upload_file(upload_url, content.video_file)
            result.add_step("File uploaded successfully")
            result.platform_response = { "upload_response": response }

            # response = self._post_content(content, upload_id)

            def is_successful(resp) -> bool:
                return 'share_id' in resp

            if is_successful(response):
                share_id = response.get('share_id')
                # TODO - Remove this hard coded live.above.3d username
                result.post_url = f"https://www.tiktok.com/@live.above.3d/video/{share_id}"
                return result.as_success(f"Video posted successfully - share ID: {share_id}")
            else:
                return result.as_failure("Failed to post to TikTok")
        except Exception as ex:
            return result.as_failure_ex("Failed to post to TikTok", ex)

    def _initialize_upload(self, content: Content) -> Dict[str, Any]:
        """
        Initialize upload session with TikTok

        Args:
            content: The content to post

        Returns:
            Upload initialization response
        """
        url = f"{self.__api_endpoint}/post/publish/video/init/"

        headers = {
            "Authorization": f"Bearer {self._require_access_token()}",
            "Content-Type": "application/json; charset=UTF-8"
        }

        video_size = Media.get_video_size_bytes(content.video_file)
        payload = {
            "post_info": self._build_post_info(content),
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": video_size,
                "chunk_size":  video_size,
                "total_chunk_count": 1
            }
        }

        # logger.debug("Initializing upload session...")
        response = requests.post(url, headers=headers, json=payload, timeout=self.__request_timeout)
        self._log_response(response)

        data = response.json()

        if data.get('data'):
            # logger.debug("Upload session initialized successfully")
            return data['data']
        else:
            error = {**data, 'status_code': response.status_code}
            raise TikTokUploadError(f"Failed to initialize upload.\n{error}")

    def _upload_file(self, upload_url: str, file_path: str) -> dict:
        """
        Upload file to TikTok

        Args:
            upload_url: Upload URL from initialization
            file_path: Path to file to upload
        """
        # logger.debug(f"Uploading file: {file_path}")

        with open(file_path, 'rb') as file:
            headers = {
                "Content-Type": "video/mp4" if file_path.endswith('.mp4') else "image/jpeg"
            }

            response = requests.put(
                upload_url,
                data=file,
                headers=headers,
                timeout=300  # 5 minutes for large files
            )
            self._log_response(response)
            response.raise_for_status()

        data = response.json()

        if response.status_code < 300:
            # logger.debug("File uploaded successfully")
            return data
        else:
            error = {**data, 'status_code': response.status_code}
            raise TikTokUploadError(f"Failed to upload file.\n{error}")

    def _post_content(self, content: Content, upload_id: str) -> Dict[str, Any]:
        """
        Publish uploaded content with metadata

        Args:
            content: Content object with metadata
            upload_id: Upload ID from initialization

        Returns:
            Publish response
        """
        url = f"{self.__api_endpoint}/post/publish/content/init/"

        headers = {
            "Authorization": f"Bearer {self._require_access_token()}",
            "Content-Type": "application/json"
        }

        source_info = {
            "source": "FILE_UPLOAD",
            "upload_id": upload_id,
            "photo_cover_index": 1,
            "photo_images": []
        }

        if content.image_file:
            source_info["photo_images"] = [content.image_file]

        payload = {
            "post_info": self._build_post_info(content),
            "source_info": source_info,
            "post_mode": "DIRECT_POST",
            "media_type": "PHOTO"
        }

        logger.debug("Publishing content...")
        response = requests.post(url, json=payload, headers=headers, timeout=self.__request_timeout)
        self._log_response(response)
        response.raise_for_status()

        data = response.json()

        if data.get('data'):
            logger.debug("Content published successfully")
            return data['data']
        else:
            error_msg = data.get('message', 'Unknown error')
            raise TikTokUploadError(f"Failed to publish content: {error_msg}")

    def _require_access_token(self)  -> str:
        if not self.__access_token:
            raise TikTokUploadError("Access has not been granted. Please first authenticate.")
        return self.__access_token

    def _build_post_info(self, content: Content) -> Dict[str, Any]:
        post_info = content.get_metadata('post_info', {
            "language": content.language_code or "en",
            "privacy_level": 'PUBLIC_TO_EVERYONE',
            "disable_duet": False,
            "disable_comment": False,
            "disable_stitch": False,
            "video_cover_timestamp_ms": 250
        })
        max_len = 2200 - 20
        post_info.update({
            "title": self._truncate_with_ellipsis(content.title or content.description),
            "description": self._truncate_with_ellipsis(content.description, max_len),
        })

        # No need as our tags are already in the description
        # # Add hashtags
        # if content.tags:
        #     # TikTok expects hashtags in description
        #     hashtags = " ".join([f"#{tag.lstrip('#')}" for tag in content.tags])
        #     post_info["description"] = f"{content.description} {hashtags}".strip()
        return post_info

    def _log_response(self, response: requests.Response):
        try:
            logger.debug(f"Response json: {response.json()}")
        except Exception:
            logger.debug(f"Response: {response}")
