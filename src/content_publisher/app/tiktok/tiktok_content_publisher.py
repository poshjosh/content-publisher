import time

import logging
import requests
from pathlib import Path
from typing import Dict, Any, Optional

from .tiktok import TikTokAPIError
from .tiktok_authenticator import TikTokAuthenticator
from .tiktok_oauth import TikTokOAuthConfig, TikTokOAuth
from ..content_publisher import SocialContentPublisher, PostType, Content, PostResult
from ..credentials import CredentialsStore, Credentials

logger = logging.getLogger(__name__)

class TikTokUploadError(TikTokAPIError):
    """Exception raised for upload failures"""
    pass


class TikTokValidationError(TikTokAPIError):
    """Exception raised for validation errors"""
    pass


class TikTokCredentials(Credentials):
    def __init__(self, data: Dict[str, Any]):
        super().__init__(data)

    def is_expired(self) -> bool:
        expires_at = self.data.get('expires_at')
        if not expires_at:
            return True
        # Add 60 second buffer
        return time.time() >= (expires_at - 60)


class TikTokContentPublisher(SocialContentPublisher):
    """Handles posting content to TikTok"""

    def __init__(self, api_endpoint: str, credentials: Dict[str, Any]):
        """
        Initialize content poster

        Args:
            api_endpoint: TikTok API base URL
            credentials: Dict containing 'client_key' and 'client_secret'
        """
        super().__init__(api_endpoint.rstrip('/'), credentials, [PostType.VIDEO, PostType.IMAGE, PostType.TEXT])
        self.supports_subtitles = False
        self.authenticator = TikTokAuthenticator(api_endpoint, credentials)
        self.credentials_store = CredentialsStore()

    def _authenticate(self) -> bool:
        filename = "tiktok.pickle"
        scopes = ["user.info.basic", "video.upload", "video.publish"]

        token_creds = self.credentials_store.load(filename, scopes)
        if token_creds:
            if token_creds.is_expired():

                self.authenticator.refresh_access_token()
                token_creds = TikTokCredentials(self.authenticator.get_credentials(scopes))
                self.credentials_store.save(filename, token_creds)
            self.authenticator.set_credentials(token_creds)
        else:
            config = TikTokOAuthConfig(
                client_key=self.credentials['client_key'],
                client_secret=self.credentials['client_secret'],
                scopes=scopes,
                redirect_uri=self.credentials['redirect_uri'],
            )
            oauth = TikTokOAuth(config)
            authorization_code: str = oauth.get_authorization_code()

            self.authenticator.get_access_token(authorization_code, oauth.get_code_verifier())

            token_creds = TikTokCredentials(self.authenticator.get_credentials(scopes))
            self.credentials_store.save(filename, token_creds)

        return token_creds.access_token is not None

    def post_content(self, content: Content, result: Optional[PostResult] = None) -> PostResult:
        """
        Post content to TikTok

        Args:
            content: Content object with video/image and metadata
            result: Optional PostResult object to track progress

        Returns:
            PostResult containing the post URL or error information

        Raises:
            TikTokValidationError: If content validation fails
            TikTokAuthenticationError: If authentication fails
            TikTokUploadError: If upload fails
        """

        if result is None:
            result = PostResult()

        try:

            if not self._authenticate():
                return result.as_auth_failure()

            result.add_step("Authenticated with TikTok API")

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
        access_token = self.authenticator.ensure_valid_token()
        url = f"{self.api_endpoint}/post/publish/video/init/"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8"
        }

        video_size = Path(content.video_file).stat().st_size

        payload = {
            "post_info": {
                "title": content.title or content.description[:100],
                "description": content.description,
                "privacy_level": content.metadata.get('privacy_level', 'SELF_ONLY') if content.metadata else 'SELF_ONLY',
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
                "video_cover_timestamp_ms": 250
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": video_size,
                "chunk_size":  video_size,
                "total_chunk_count": 1
            }
        }

        try:
            # logger.debug("Initializing upload session...")
            response = requests.post(url, headers=headers, json=payload, timeout=30)

            data = response.json()

            if data.get('data'):
                # logger.debug("Upload session initialized successfully")
                return data['data']
            else:
                error = {**data, 'status_code': response.status_code}
                raise TikTokUploadError(f"Failed to initialize upload.\n{error}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Upload initialization failed: {e}")
            raise TikTokUploadError(f"Upload initialization failed: {e}")

    def _upload_file(self, upload_url: str, file_path: str) -> dict:
        """
        Upload file to TikTok

        Args:
            upload_url: Upload URL from initialization
            file_path: Path to file to upload
        """
        try:
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
                response.raise_for_status()

            data = response.json()

            if response.status_code < 300:
                # logger.debug("File uploaded successfully")
                return data
            else:
                error = {**data, 'status_code': response.status_code}
                raise TikTokUploadError(f"Failed to upload file.\n{error}")

        except requests.exceptions.RequestException as e:
            logger.error(f"File upload failed: {e}")
            raise TikTokUploadError(f"File upload failed: {e}")
        except IOError as e:
            logger.error(f"File read error: {e}")
            raise TikTokUploadError(f"File read error: {e}")

    def _post_content(self, content: Content, upload_id: str) -> Dict[str, Any]:
        """
        Publish uploaded content with metadata

        Args:
            content: Content object with metadata
            upload_id: Upload ID from initialization

        Returns:
            Publish response
        """
        access_token = self.authenticator.ensure_valid_token()
        url = f"{self.api_endpoint}/post/publish/content/init/"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        # Build post info
        post_info = {
            "title": content.title or content.description[:100],
            "description": content.description,
            "privacy_level": "PUBLIC_TO_EVERYONE",
            "disable_duet": False,
            "disable_comment": False,
            "disable_stitch": False,
            "video_cover_timestamp_ms": 1000
        }

        source_info = {
            "source": "FILE_UPLOAD",
            "upload_id": upload_id,
            "photo_cover_index": 1,
            "photo_images": []
        }

        if content.image_file:
            source_info["photo_images"] = [content.image_file]

        if content.language_code:
            post_info["language"] = content.language_code

        # No need as our tags are already in the description
        # # Add hashtags
        # if content.tags:
        #     # TikTok expects hashtags in description
        #     hashtags = " ".join([f"#{tag.lstrip('#')}" for tag in content.tags])
        #     post_info["description"] = f"{content.description} {hashtags}".strip()

        payload = {
            "post_info": post_info,
            "source_info": source_info,
            "post_mode": "DIRECT_POST",
            "media_type": "PHOTO"
        }

        try:
            logger.debug("Publishing content...")
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()

            if data.get('data'):
                logger.debug("Content published successfully")
                return data['data']
            else:
                error_msg = data.get('message', 'Unknown error')
                raise TikTokUploadError(f"Failed to publish content: {error_msg}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Content publish failed: {e}")
            raise TikTokUploadError(f"Content publish failed: {e}")