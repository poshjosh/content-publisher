import logging

from typing import Dict, Any, Optional

import praw
from praw.models import InlineImage, InlineVideo

from ..content_publisher import SocialContentPublisher, PostType, Content, PostResult, PostRequest

logger = logging.getLogger(__name__)


class RedditContentPublisher(SocialContentPublisher):
    def __init__(self, _, credentials: Dict[str, Any]):
        super().__init__([PostType.VIDEO, PostType.IMAGE, PostType.TEXT])
        self.__credentials = credentials
        self.reddit = None

    def authenticate(self, request: PostRequest):
        self.reddit = praw.Reddit(
            client_id=self.__credentials['client_id'],
            client_secret=self.__credentials['client_secret'],
            user_agent=self.__credentials.get('user_agent', 'Social Media Poster'),
            username=self.__credentials['username'],
            password=self.__credentials['password']
        )

        # Test authentication
        self.reddit.user.me()

    def post_content(self, request: PostRequest, result: Optional[PostResult] = None) -> PostResult:
        """Post content to Reddit"""
        if result is None:
            result = PostResult()
        try:

            subreddit = self.__credentials.get('subreddit')
            if not subreddit:
                return result.as_failure("Subreddit not specified.")

            subreddit: praw.models.Subreddit = self.reddit.subreddit(subreddit)

            content: Content = request.content

            title = self._truncate_with_ellipsis(content.title or content.description)

            max_len = 40000 - 400
            submission: praw.models.Submission = subreddit.submit(
                title=title,
                selftext=self._truncate_with_ellipsis(content.description, max_len)
            )
            result.add_step("Text content submitted to Reddit")

            approve: bool = bool(request.get('approve', True))

            try:
                submission = self.add_media_to_submission(submission, content, title)

                result.add_step("Successfully added media to Reddit post")

                media_added = True

            except Exception as ex:

                media_added = False

                result.add_step(f"Failed to add media to Reddit post. Reason: {str(ex)}", logging.WARNING)

            result.add_step(f"Post submitted{' successfully' if media_added else ''} - ID: {submission.id}")

            if approve and media_added:
                try:
                    submission.mod.approve()
                    result.add_step("Reddit post approved")
                except Exception as ex:
                    result.add_step(f"Failed to approve Reddit post. Reason: {str(ex)}", logging.WARNING)

            result.post_url = submission.url
            result.platform_response = {'id': submission.id, 'url': submission.url}
            return result.as_success(f"Content posted{' successfully' if media_added else ''} to Reddit")

        except Exception as ex:
            return result.as_failure_ex("Failed to post to Reddit", ex)

    @staticmethod
    def add_media_to_submission(submission: praw.models.Submission, content: Content, title) -> praw.models.Submission:
        if not content.video_file or not content.image_file:
            return submission
        if content.video_file:
            media = InlineVideo(path=content.video_file, caption=f"video for article: {title}")
        else:
            media = InlineImage(path=content.image_file, caption=f"image for article: {title}")

        body = "{media}\n\n" + content.description

        if not hasattr(submission, 'media_metadata'):
            submission.media_metadata = { "media": media }

        return submission._edit_experimental(body, inline_media={ "media": media })



