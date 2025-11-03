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
    def api_version(self) -> str:
        raise NotImplementedError

    @property
    def credentials(self) -> dict[str, Any]:
        raise NotImplementedError

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(endpoint={self.endpoint}, credentials={self.credentials.keys()})"


class FacebookPublisherConfig(PublisherConfig):
    @property
    def endpoint(self) -> str:
        return f"https://graph.facebook.com/{self.api_version}"

    @property
    def api_version(self) -> str:
        return "v24.0"

    @property
    def credentials(self) -> dict[str, Any]:
        credentials = {
            'client_id': os.environ[f"{_PREFIX}_FACEBOOK_CLIENT_ID"],
            'client_secret': os.environ[f"{_PREFIX}_FACEBOOK_CLIENT_SECRET"],
            'redirect_uri': 'http://localhost:8080/callback',
            'api_version': self.api_version
        }
        page_id = os.environ.get(f"{_PREFIX}_FACEBOOK_PAGE_ID")
        if page_id:
            credentials['page_id'] = page_id
        return credentials


class RedditPublisherConfig(PublisherConfig):
    @property
    def endpoint(self) -> str:
        return "https://www.reddit.com/dev/api"

    @property
    def api_version(self) -> str:
        return ""

    @property
    def credentials(self) -> dict[str, Any]:
        app_id = "https://github.com/poshjosh/content-publisher"
        app_version = "0.0.11"
        username = os.environ[f"{_PREFIX}_REDDIT_USERNAME"]
        return {
            'client_id': os.environ[f"{_PREFIX}_REDDIT_CLIENT_ID"],
            'client_secret': os.environ[f"{_PREFIX}_REDDIT_CLIENT_SECRET"],
            'user_agent': f"python:{app_id}:{app_version} (by {username})",
            'username': username,
            'password': os.environ[f"{_PREFIX}_REDDIT_PASSWORD"],
            'subreddit': os.environ.get(f"{_PREFIX}_REDDIT_SUBREDDIT", "test"),
            'api_version': self.api_version
        }


class TikTokPublisherConfig(PublisherConfig):
    @property
    def endpoint(self) -> str:
        return f"https://open.tiktokapis.com/{self.api_version}"

    @property
    def api_version(self) -> str:
        return "v2"

    @property
    def credentials(self) -> dict[str, Any]:
        return {
            'client_key': os.environ[f"{_PREFIX}_TIKTOK_CLIENT_KEY"],
            'client_secret': os.environ[f"{_PREFIX}_TIKTOK_CLIENT_SECRET"],
            'redirect_uri': 'http://localhost:8080/callback',
            'api_version': self.api_version
        }


class XPublisherConfig(PublisherConfig):
    @property
    def endpoint(self) -> str:
        return f"https://api.twitter.com/{self.api_version}"

    @property
    def api_version(self) -> str:
        return "2"

    @property
    def credentials(self) -> dict[str, Any]:
        return {
            'consumer_key': os.environ[f"{_PREFIX}_X_API_KEY"],
            'consumer_secret': os.environ[f"{_PREFIX}_X_API_KEY_SECRET"],
            'access_token': os.environ[f"{_PREFIX}_X_ACCESS_TOKEN"],
            'access_token_secret': os.environ[f"{_PREFIX}_X_ACCESS_TOKEN_SECRET"],
            'bearer_token': os.environ[f"{_PREFIX}_X_BEARER_TOKEN"],
            'api_version': self.api_version
        }


class YouTubePublisherConfig(PublisherConfig):
    @property
    def endpoint(self) -> str:
        return f"https://www.googleapis.com/youtube/{self.api_version}"

    @property
    def api_version(self) -> str:
        return "v3"

    @property
    def credentials(self) -> dict[str, Any]:
        return {
            "client_id": os.environ[f"{_PREFIX}_GOOGLE_CLIENT_ID"],
            "client_secret": os.environ[f"{_PREFIX}_GOOGLE_CLIENT_SECRET"],
            'api_version': self.api_version
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