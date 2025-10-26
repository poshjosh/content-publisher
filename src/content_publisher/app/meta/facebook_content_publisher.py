import logging

from typing import Dict, Any, Optional

import facebook

from ..content_publisher import SocialContentPublisher, PostType, Content, PostResult

logger = logging.getLogger(__name__)


class FacebookContentPublisher(SocialContentPublisher):
    """Handler for Facebook/Meta API"""

    def __init__(self, api_endpoint: str, credentials: Dict[str, Any]):
        super().__init__(api_endpoint, credentials, [PostType.VIDEO, PostType.IMAGE, PostType.TEXT])
        self.supports_subtitles = False
        self.graph = None

    def _authenticate(self) -> bool:
        """Authenticate with Facebook Graph API"""
        try:
            access_token = self.credentials.get('access_token')
            if not access_token:
                return False

            self.graph = facebook.GraphAPI(access_token=access_token)
            # Test the connection
            self.graph.get_object('me')
            return True
        except Exception as ex:
            logger.error(f"Facebook authentication failed: {ex}")
            return False

    def post_content(self, content: Content, result: Optional[PostResult] = None) -> PostResult:
        """Post content to Facebook"""
        if result is None:
            result = PostResult()
        try:
            if not self._authenticate():
                return result.as_auth_failure()

            result.add_step("Authenticated with Facebook API")

            page_id = self.credentials.get('page_id', 'me')

            if content.video_file:
                # Post video
                with open(content.video_file, 'rb') as video_file:
                    response = self.graph.put_video(
                        video=video_file,
                        description=content.description,
                        title=content.title
                    )
            elif content.image_file:
                # Post photo
                with open(content.image_file, 'rb') as image_file:
                    response = self.graph.put_photo(
                        image=image_file,
                        message=content.description
                    )
            else:
                # Post text only
                response = self.graph.put_object(
                    parent_object=page_id,
                    connection_name='feed',
                    message=content.description
                )

            post_id = response.get('id') or response.get('post_id')
            result.add_step(f"Content posted successfully - ID: {post_id}")
            result.post_url = f"https://www.facebook.com/{post_id}"
            result.platform_response = response
            result.success = True
            return result.as_success("Content posted successfully to Facebook")

        except Exception as ex:
            return result.as_failure_ex("Failed to post to Facebook", ex)