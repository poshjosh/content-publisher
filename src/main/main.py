#!/usr/bin/env python3
import logging

from app.config import Config
from app.content_publisher import Content, SocialMediaPoster, PostRequest, PostResult
from app.content_publisher import SocialPlatformApiConfig
from app.run_arg import RunArg

def publish_content(config: Config, platforms: list[str], content: Content) -> dict[str, PostResult]:

    poster = SocialMediaPoster()

    result = {}

    for platform in platforms:

        publisher_config = config.get_publisher_config(platform)

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


if __name__ == "__main__":
    run_args = RunArg.get()

    logging.basicConfig(
        level=logging.DEBUG if run_args.get(RunArg.VERBOSE) is True else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    platforms = run_args.get(RunArg.PLATFORMS)
    dir_path = run_args.get(RunArg.DIR)
    text_title = run_args.get(RunArg.TEXT_TITLE)
    media_orientation = run_args.get(RunArg.MEDIA_ORIENTATION)

    content = Content.of_dir(dir_path, text_title, media_orientation)
    publish_content(Config(), platforms, content)