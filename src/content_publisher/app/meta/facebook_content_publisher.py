import logging

from typing import Dict, Any, Optional

import facebook

from ..content_publisher import SocialContentPublisher, PostType, Content, PostResult, PostRequest
from .facebook_oauth import FacebookOAuth

logger = logging.getLogger(__name__)


class FacebookContentPublisher(SocialContentPublisher):
    def __init__(self, api_endpoint: str, credentials: Dict[str, Any]):
        super().__init__([PostType.VIDEO, PostType.IMAGE, PostType.TEXT])
        self.__api_endpoint = api_endpoint
        self.__credentials = credentials
        self.__page_id = credentials.get('page_id')
        self.graph = None

    def authenticate(self, request: PostRequest):
        permissions = request.get("credentials_scopes", [
            'pages_show_list',
            'pages_read_engagement',
            'pages_manage_posts',
            'pages_manage_engagement'
        ])
        credentials_filename = request.get("credentials_filename", "facebook.pickle")

        oauth = FacebookOAuth(self.__api_endpoint, {**self.__credentials, **request.post_config})

        access_token = oauth.get_credentials_interactively(
            permissions, credentials_filename).access_token

        if self.__page_id:
            access_token, page = oauth.get_page_access_token(self.__page_id, access_token)
            logger.debug(f"Using page ID: {self.__page_id} => {page['id']}")
            self.__page_id = page['id']

        self.graph = facebook.GraphAPI(access_token=access_token)

        # Test the connection
        self.graph.get_object('me')

    def post_content(self, request: PostRequest, result: Optional[PostResult] = None) -> PostResult:
        if result is None:
            result = PostResult()
        try:
            target_id = self.__page_id or 'me'

            content: Content = request.content

            if content.video_file:
                # Post video and text content
                with open(content.video_file, 'rb') as video_file:
                    # facebook.GraphAPIError: (#100) The global id 100092339087423 is not allowed for this call
                    max_len = 50000 #63206
                    post_args = {
                        "source": ("video", video_file),
                        "title": self._truncate_with_ellipsis(content.title or content.description),
                        "description": self._truncate_with_ellipsis(content.description, max_len),
                    }
                    # facebook.GraphAPIError: (#100) No permission to publish the video
                    response = self.graph.request(
                        "{0}/{1}".format(self.graph.version, f"{target_id}/videos"),
                        post_args=post_args,
                        method="POST"
                    )

            elif content.image_file:
                # Post photo
                with open(content.image_file, 'rb') as image_file:
                    response = self.graph.put_photo(
                        image=image_file,
                        album_path=f"{target_id}/photos",
                        message=content.description
                    )
            else:
                # Post text only
                response = self.graph.put_object(
                    parent_object=target_id,
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