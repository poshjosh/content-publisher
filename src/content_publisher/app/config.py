from abc import ABC

import os

from typing import Any

_PREFIX = "CONTENT_PUBLISHER"

class PublisherConfig(ABC):
    @property
    def endpoint(self) -> str:
        raise NotImplementedError

    @property
    def credentials(self) -> dict[str, Any]:
        raise NotImplementedError

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(endpoint={self.endpoint}, credentials={self.credentials.keys()})"

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

class TwitterPublisherConfig(PublisherConfig):
    @property
    def endpoint(self) -> str:
        return "https://api.twitter.com/2"

    @property
    def credentials(self) -> dict[str, Any]:
        return {
            'consumer_key': os.environ[f"{_PREFIX}_TWITTER_CONSUMER_KEY"],
            'consumer_secret': os.environ[f"{_PREFIX}_TWITTER_CONSUMER_SECRET"],
            'access_token': os.environ[f"{_PREFIX}_TWITTER_ACCESS_TOKEN"],
            'access_token_secret': os.environ[f"{_PREFIX}_TWITTER_ACCESS_TOKEN_SECRET"]
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

class Config:
    def __init__(self):
        self.__configs = {
            "youtube": YouTubePublisherConfig(),
            "facebook": FacebookPublisherConfig(),
            "x": TwitterPublisherConfig(),
            "twitter": TwitterPublisherConfig(),
            "reddit": RedditPublisherConfig()
        }

    def get_publisher_config(self, platform: str) -> PublisherConfig:
        platform = platform.lower()
        result = self.__configs.get(platform)
        if not result:
            raise ValueError(f"Unsupported platform: {platform}")
        return result