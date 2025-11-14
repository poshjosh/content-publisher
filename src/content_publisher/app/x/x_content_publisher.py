import logging

from typing import Dict, Any, Optional

import tweepy

from ..content_publisher import SocialContentPublisher, PostType, Content, PostResult, PostRequest

logger = logging.getLogger(__name__)


class XContentPublisher(SocialContentPublisher):
    def __init__(self, _, credentials: Dict[str, Any]):
        super().__init__([PostType.VIDEO, PostType.IMAGE, PostType.TEXT])
        self.__credentials = credentials
        self.api_v1 = Optional[tweepy.API]
        self.api_v2 = Optional[tweepy.Client]

    def authenticate(self, request: PostRequest):
        self.api_v1 = XContentPublisher._authenticated_api_v1(self.__credentials)
        self.api_v2 = XContentPublisher._authenticated_api_v2(self.__credentials)

    def post_content(self, request: PostRequest, result: Optional[PostResult] = None) -> PostResult:
        """Post content to Twitter/X"""
        if result is None:
            result = PostResult()
        try:

            media_ids = []

            content: Content = request.content

            media_id = self._upload_media(content.image_file, "tweet_image", result)
            if media_id:
                media_ids.append(media_id)

            # media_id = self._upload_media(content.video_file, "tweet_video", result)
            # if media_id:
            #     media_ids.append(media_id)

            max_len = 280 - 5
            tweet_text = f"{content.title}\n\n{content.description}" if content.title else content.description
            tweet_text = self._truncate_with_ellipsis(tweet_text, max_len)

            if media_ids:
                response = self.api_v2.create_tweet(text=tweet_text, media_ids=media_ids)
            else:
                response = self.api_v2.create_tweet(text=tweet_text)

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

    def _upload_media(self, media_file: Optional[str], media_category: str, result: PostResult) -> Optional[str]:
        if not media_file:
            return None
        try:
            media = self.api_v1.media_upload(media_file, media_category=media_category)
            if media and media.media_id:
                result.add_step(f"Image uploaded, ID: {media.media_id}")
                return media.media_id
            else:
                result.add_step(f"Failed to upload image to X: {media_file}. Response: {media}", logging.WARNING)
                return None
        except Exception as ex:
            message = f"Failed to upload image to X: {media_file}"
            logger.exception(message, exc_info=ex)
            result.add_step(message, logging.WARNING)
            return None

    @staticmethod
    def _authenticated_api_v1(credentials: Dict[str, Any]) -> tweepy.API:
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

    @staticmethod
    def _authenticated_api_v2(credentials: Dict[str, Any]) -> tweepy.Client:
        client = tweepy.Client(
            bearer_token=credentials['bearer_token'],
            consumer_key=credentials['consumer_key'],
            consumer_secret=credentials['consumer_secret'],
            access_token=credentials['access_token'],
            access_token_secret=credentials['access_token_secret']
        )
        client.get_recent_tweets_count("from:TwitterAPI")
        return client
