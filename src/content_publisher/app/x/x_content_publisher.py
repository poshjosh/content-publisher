import logging

from typing import Dict, Any, Optional

import tweepy

from ..content_publisher import SocialContentPublisher, PostType, Content, PostResult

logger = logging.getLogger(__name__)


class XContentPublisher(SocialContentPublisher):
    def __init__(self, api_endpoint: str, credentials: Dict[str, Any]):
        super().__init__(api_endpoint, credentials,
                         [PostType.VIDEO, PostType.IMAGE, PostType.TEXT])
        self.supports_subtitles = False
        self.api_v1 = Optional[tweepy.API]
        self.api_v2 = Optional[tweepy.Client]

    def _authenticate(self) -> bool:
        try:
            self.api_v1 = XContentPublisher._authenticated_api_v1(self.credentials)
            if self.api_v1 is None:
                return False
            self.api_v2 = XContentPublisher._authenticated_api_v2(self.credentials)
            return self.api_v2 is not None
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
                media = self.api_v1.media_upload(content.image_file)
                media_ids.append(media.media_id)
                result.add_step(f"Image uploaded, ID: {media.media_id}")

            # if content.video_file:
            #     media = self.api_v1.media_upload(content.video_file)
            #     media_ids.append(media.media_id)
            #     result.add_step(f"Video uploaded, ID: {media.media_id}")

            # Post tweet
            tweet_text = content.description[:280]  # Twitter character limit
            if content.title:
                tweet_text = f"{content.title}\n\n{content.description}"[:280]

            response = self.api_v2.create_tweet(text=tweet_text, media_ids=media_ids)
            result.platform_response = { "raw": response }

            if isinstance(response, tweepy.Response):
                result.platform_response = response.data
                tweet_id = response.data.get("id")
                result.add_step(f"Content posted successfully, ID: {tweet_id}")
                result.post_url = f"https://twitter.com/user/status/{tweet_id}"
                return result.as_success("Content posted successfully to X")
            else:
                return result.as_failure("Failed to post to X")

        except Exception as ex:
            return result.as_failure_ex("Failed to post to X", ex)

    @staticmethod
    def _authenticated_api_v1(credentials: Dict[str, Any]) -> Optional[tweepy.API]:
        try:
            auth = tweepy.OAuth1UserHandler(
                consumer_key=credentials['consumer_key'],
                consumer_secret=credentials['consumer_secret'],
                access_token=credentials['access_token'],
                access_token_secret=credentials['access_token_secret']
            )

            api_v1 = tweepy.API(auth)
            # Test authentication
            api_v1.verify_credentials()
            return api_v1
        except Exception as ex:
            logger.error(f"Twitter authentication for API v1 failed: {ex}")
            return None

    @staticmethod
    def _authenticated_api_v2(credentials: Dict[str, Any]) -> Optional[tweepy.Client]:
        try:
            client = tweepy.Client(
                bearer_token=credentials['bearer_token'],
                consumer_key=credentials['consumer_key'],
                consumer_secret=credentials['consumer_secret'],
                access_token=credentials['access_token'],
                access_token_secret=credentials['access_token_secret']
            )
            client.get_recent_tweets_count("from:TwitterAPI")
            return client
        except Exception as ex:
            logger.error(f"Twitter authentication for API v2 failed: {ex}")
            return None
