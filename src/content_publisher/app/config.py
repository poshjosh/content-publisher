from enum import Enum, unique

from abc import ABC

import os

from typing import Any

_PREFIX = "CONTENT_PUBLISHER"


@unique
class SocialPlatformType(Enum):
    """Supported social media platforms"""
    FACEBOOK = "facebook"
    META = "meta"  # Alias for facebook
    REDDIT = "reddit"
    TIKTOK = "tiktok"
    TWITTER = "twitter" # Alias for x
    X = "x"
    YOUTUBE = "youtube"

    @staticmethod
    def values() -> list[str]:
        return [str(SocialPlatformType(e).value) for e in SocialPlatformType]


class PublisherConfig(ABC):
    @property
    def endpoint(self) -> str:
        raise NotImplementedError

    @property
    def credentials(self) -> dict[str, Any]:
        raise NotImplementedError

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(endpoint={self.endpoint}, credentials={self.credentials.keys()})"


class FacebookPublisherConfig(PublisherConfig):
    @property
    def endpoint(self) -> str:
        return "https://graph.facebook.com/v18.0"

    @property
    def credentials(self) -> dict[str, Any]:
        return {
            'access_token': os.environ[f"{_PREFIX}_FACEBOOK_ACCESS_TOKEN"],
            'page_id': os.environ[f"{_PREFIX}_FACEBOOK_PAGE_ID"]
        }


class RedditPublisherConfig(PublisherConfig):
    @property
    def endpoint(self) -> str:
        return "https://www.reddit.com/dev/api"

    @property
    def credentials(self) -> dict[str, Any]:
        app_id = "https://github.com/poshjosh/content-publisher"
        app_version = "0.0.7"
        username = os.environ[f"{_PREFIX}_REDDIT_USERNAME"]
        return {
            'client_id': os.environ[f"{_PREFIX}_REDDIT_CLIENT_ID"],
            'client_secret': os.environ[f"{_PREFIX}_REDDIT_CLIENT_SECRET"],
            'user_agent': f"python:{app_id}:{app_version} (by {username})",
            'username': username,
            'password': os.environ[f"{_PREFIX}_REDDIT_PASSWORD"],
            'subreddit': os.environ.get(f"{_PREFIX}_REDDIT_SUBREDDIT", "test"),
        }


class TikTokPublisherConfig(PublisherConfig):
    @property
    def endpoint(self) -> str:
        return "https://open.tiktokapis.com/v2"

    @property
    def credentials(self) -> dict[str, Any]:
        return {
            'client_key': os.environ[f"{_PREFIX}_TIKTOK_CLIENT_KEY"],
            'client_secret': os.environ[f"{_PREFIX}_TIKTOK_CLIENT_SECRET"],
            'redirect_uri': 'http://localhost:8080/callback'
        }


class XPublisherConfig(PublisherConfig):
    @property
    def endpoint(self) -> str:
        return "https://api.twitter.com/2"

    @property
    def credentials(self) -> dict[str, Any]:
        return {
            'consumer_key': os.environ[f"{_PREFIX}_X_CONSUMER_KEY"],
            'consumer_secret': os.environ[f"{_PREFIX}_X_CONSUMER_SECRET"],
            'access_token': os.environ[f"{_PREFIX}_X_ACCESS_TOKEN"],
            'access_token_secret': os.environ[f"{_PREFIX}_X_ACCESS_TOKEN_SECRET"]
        }


class YouTubePublisherConfig(PublisherConfig):
    @property
    def endpoint(self) -> str:
        return "https://www.googleapis.com/youtube/v3"

    @property
    def credentials(self) -> dict[str, Any]:
        return {
            "client_id": os.environ[f"{_PREFIX}_GOOGLE_CLIENT_ID"],
            "client_secret": os.environ[f"{_PREFIX}_GOOGLE_CLIENT_SECRET"]
        }


class ConfigFactory:
    def __init__(self):
        self.__configs = {
            SocialPlatformType.FACEBOOK.value: FacebookPublisherConfig(),
            SocialPlatformType.META.value: FacebookPublisherConfig(),
            SocialPlatformType.REDDIT.value: RedditPublisherConfig(),
            SocialPlatformType.TIKTOK.value: TikTokPublisherConfig(),
            SocialPlatformType.TWITTER.value: XPublisherConfig(),
            SocialPlatformType.X.value: XPublisherConfig(),
            SocialPlatformType.YOUTUBE.value: YouTubePublisherConfig()
        }

    def get_publisher_config(self, platform: str) -> PublisherConfig:
        platform = platform.lower()
        result = self.__configs.get(platform)
        if not result:
            raise ValueError(f"Unsupported platform: {platform}")
        return result