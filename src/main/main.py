#!/usr/bin/env python3
import os

import logging

from app.config import Config
from app.content_publisher import ContentObject, SocialMediaPoster, SocialMediaRequest

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def publish_content(config: Config, platforms: list[str], dir_path: str):
    """Example usage of the Social Media Poster"""

    file_path = f"{dir_path}/content.txt"
    file_content = None

    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            file_content = f.read()
            print(f"Read {len(file_content)} chars")
    else:
        raise ValueError(f"File not found: {file_path}")

    def is_valid_lang_code(code) -> bool:
        return (len(code) == 2 and code.isalpha()) or (len(code) == 5 and code[2] == '-' and code[:2].isalpha() and code[3:].isalpha())

    subtitles_dir_path = f"{dir_path}/subtitles"
    print(f"Checking subtitles directory: {subtitles_dir_path}")
    subtitle_files = {}
    if os.path.exists(subtitles_dir_path):
        for file_name in os.listdir(subtitles_dir_path):
            if file_name.endswith('.srt') or file_name.endswith('.vtt'):
                lang_code = file_name.split('.')[-2]
                if not is_valid_lang_code(lang_code):
                    print(f"Skipping invalid lang code: {lang_code} for file path: {file_name}")
                    continue
                subtitle_files[lang_code] = os.path.join(subtitles_dir_path, file_name)
                print(f"Found subtitle file for {lang_code}={file_name}")

    video_file_path = f"{dir_path}/video-portrait.mp4"
    if not os.path.exists(video_file_path):
        raise ValueError(f"Video file not found: {video_file_path}")

    # Example content object
    content = ContentObject(
        title="Days of signs and wonders are here! #shorts",
        description=file_content,
        video_file=video_file_path,
        subtitle_files=subtitle_files
    )

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
    publish_content(config, platforms, dir_path)
