#!/usr/bin/env python3
import logging

from app.config import Config
from app.content_publisher import Content, SocialMediaPoster, PostRequest
from app.content_publisher import SocialPlatformApiConfig

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def publish_content(config: Config, platforms: list[str], content: Content):

    poster = SocialMediaPoster()

    for platform in platforms:
        print(f"\nTesting {platform}")

        publisher_config = config.get_publisher_config(platform)
        print(f"Publisher config:\n{publisher_config}")

        request = PostRequest(
            api_config=SocialPlatformApiConfig(
                platform_name=platform,
                api_endpoint=publisher_config.endpoint,
                api_credentials=publisher_config.credentials,
            ),
            content=content
        )

        result = poster.post_content(request)

        print("========= RESULT ==========")
        print(result)
        print("===========================")


if __name__ == "__main__":
    config = Config()
    # platforms = ["youtube", "facebook", "x", "tiktok"]
    platforms = ["youtube"]
    dir_path = "/Users/chinomso/dev_ai/content-publisher/git-ignore/test-content/signs-and-wonders"
    content = Content.of_dir(dir_path, "The days of signs and wonders! #shorts", "landscape")
    publish_content(config, platforms, content)