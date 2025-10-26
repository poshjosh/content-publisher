#!/usr/bin/env python3
from .config import ConfigFactory
from .content_publisher import Content, PostRequest, PostResult, SocialMediaPoster, SocialPlatformApiConfig

class App:
    def __init__(self, config_factory: ConfigFactory = ConfigFactory()):
        self.config_factory = config_factory

    def publish_content(self, platforms: list[str], content: Content) -> dict[str, PostResult]:

        poster = SocialMediaPoster()

        result = {}

        for platform in platforms:

            publisher_config = self.config_factory.get_publisher_config(platform)

            request = PostRequest(
                api_config=SocialPlatformApiConfig(
                    platform_name=platform,
                    api_endpoint=publisher_config.endpoint,
                    api_credentials=publisher_config.credentials,
                ),
                content=content
            )

            result[platform] = poster.post_content(request)

        return result