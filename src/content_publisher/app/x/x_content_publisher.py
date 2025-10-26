import logging

from typing import Dict, Any, Optional

import tweepy

from ..content_publisher import SocialContentPublisher, PostType, Content, PostResult

logger = logging.getLogger(__name__)


class XContentPublisher(SocialContentPublisher):
    """Handler for X (Twitter) API"""

    def __init__(self, api_endpoint: str, credentials: Dict[str, Any]):
        super().__init__(api_endpoint, credentials, [PostType.VIDEO, PostType.IMAGE, PostType.TEXT])
        self.supports_subtitles = False
        self.api = None

    def _authenticate(self) -> bool:
        """Authenticate with Twitter API"""
        try:
            auth = tweepy.OAuth1UserHandler(
                consumer_key=self.credentials['consumer_key'],
                consumer_secret=self.credentials['consumer_secret'],
                access_token=self.credentials['access_token'],
                access_token_secret=self.credentials['access_token_secret']
            )

            self.api = tweepy.API(auth)
            # Test authentication
            self.api.verify_credentials()
            return True
        except Exception as ex:
            logger.error(f"Twitter authentication failed: {ex}")
            return False

    def post_content(self, content: Content, result: Optional[PostResult] = None) -> PostResult:
        """Post content to Twitter/X"""
        if result is None:
            result = PostResult()
        try:
            if not self._authenticate():
                return result.as_auth_failure()

            result.add_step("Authenticated with Twitter API")

            media_ids = []

            # Upload media if present
            if content.image_file:
                media = self.api.media_upload(content.image_file)
                media_ids.append(media.media_id)
                result.add_step("Image uploaded")

            if content.video_file:
                media = self.api.media_upload(content.video_file)
                media_ids.append(media.media_id)
                result.add_step("Video uploaded")

            # Post tweet
            tweet_text = content.description[:280]  # Twitter character limit
            if content.title:
                tweet_text = f"{content.title}\n\n{content.description}"[:280]

            tweet = self.api.update_status(
                status=tweet_text,
                media_ids=media_ids if media_ids else None
            )

            result.add_step(f"Tweet posted successfully - ID: {tweet.id}")
            result.post_url = f"https://twitter.com/user/status/{tweet.id}"
            result.platform_response = tweet._json
            return result.as_success("Content posted successfully to X")

        except Exception as ex:
            return result.as_failure_ex("Failed to post to X", ex)