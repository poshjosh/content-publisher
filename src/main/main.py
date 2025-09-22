#!/usr/bin/env python3
import logging

from app.config import Config
from app.content_publisher import Content, SocialMediaPoster, SocialMediaRequest

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

        request = SocialMediaRequest(
            platform_name=platform,
            api_endpoint=publisher_config.endpoint,
            api_credentials=publisher_config.credentials,
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
    dir_path = "/Users/chinomso/dev_ai/content-publisher/git-ignore/test-content/advice"
    content = Content.of_dir(dir_path, "RAPTURE - Out of reverence for Jesus. #shorts", "portrait")
    publish_content(config, platforms, content)
