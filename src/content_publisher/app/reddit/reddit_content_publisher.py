import logging

from typing import Dict, Any, Optional

import praw
from praw.models import InlineImage, InlineVideo

from ..content_publisher import SocialContentPublisher, PostType, Content, PostResult

logger = logging.getLogger(__name__)


class RedditContentPublisher(SocialContentPublisher):
    """Handler for Reddit API"""

    def __init__(self, api_endpoint: str, credentials: Dict[str, Any]):
        super().__init__(api_endpoint, credentials, [PostType.VIDEO, PostType.IMAGE, PostType.TEXT])
        self.supports_subtitles = False
        self.reddit = None

    def _authenticate(self) -> bool:
        """Authenticate with Reddit API"""
        try:
            self.reddit = praw.Reddit(
                client_id=self.credentials['client_id'],
                client_secret=self.credentials['client_secret'],
                user_agent=self.credentials.get('user_agent', 'Social Media Poster'),
                username=self.credentials['username'],
                password=self.credentials['password']
            )

            # Test authentication
            self.reddit.user.me()
            return True
        except Exception as ex:
            logger.error(f"Reddit authentication failed: {ex}")
            return False

    def post_content(self, content: Content, result: Optional[PostResult] = None) -> PostResult:
        """Post content to Reddit"""
        if result is None:
            result = PostResult()
        try:

            subreddit = self.credentials.get('subreddit')
            if not subreddit:
                return result.as_failure("Subreddit not specified.")

            if not self._authenticate():
                return result.as_auth_failure()

            result.add_step("Authenticated with Reddit API")

            subreddit = self.reddit.subreddit(subreddit)

            title = content.title or content.description[:100]

            submission = subreddit.submit(
                title=title,
                selftext=content.description
            )

            approve: bool = True

            if content.video_file or content.image_file:
                try:
                    if content.video_file:
                        media = InlineVideo(path=content.video_file,
                                            caption=f"video for article: {title}")
                    else:
                        media = InlineImage(path=content.image_file,
                                            caption=f"image for article: {title}")
                    body = "{media}\n\n" + content.description
                    if not hasattr(submission, 'media_metadata'):
                        submission.media_metadata = { "media": media }
                    submission = submission._edit_experimental(body, inline_media={ "media": media })

                except Exception as ex:

                    approve = False

                    result.add_step(f"Failed to add media to post. Reason: {str(ex)}", logging.WARNING)

            result.add_step(f"Post submitted successfully - ID: {submission.id}")

            if approve:
                submission.mod.approve()
                result.add_step("Post approved")

            result.post_url = submission.url
            result.platform_response = {'id': submission.id, 'url': submission.url}
            return result.as_success("Content posted successfully to Reddit")

        except Exception as ex:
            return result.as_failure_ex("Failed to post to Reddit", ex)

