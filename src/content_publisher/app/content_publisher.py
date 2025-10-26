#!/usr/bin/env python3
"""
Social Media Content Posting System

A comprehensive system for posting content to multiple social media platforms
with support for videos, images, text, and subtitles where supported.

Supported platforms: Facebook (Meta), Reddit, TikTok, X (Twitter), YouTube
Note:
    TikTok does not have a public API and is not supported.
    Instagram API is limited

"""

import os
import logging

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime
from enum import Enum

from .config import SocialPlatformType

logger = logging.getLogger(__name__)

class PostType(Enum):
    VIDEO = "video"
    IMAGE = "image"
    TEXT = "text"

@dataclass
class SocialPlatformApiConfig:
    platform_name: str
    api_endpoint: str
    api_credentials: Dict[str, Any]
    
    def __str__(self) -> str:
        return (f"{self.__class__.__name__}-{self.platform_name} "
                f"(endpoint={self.api_endpoint}, credentials={self.api_credentials.keys()})")

@dataclass
class Content:
    """Content object containing all media and metadata"""
    description: str
    video_file: Optional[str] = None
    image_file: Optional[str] = None
    title: Optional[str] = None
    language_code: Optional[str] = None
    tags: Optional[List[str]] = None
    subtitle_files: Optional[Dict[str, str]] = None  # {'en': 'path/to/en.srt', 'es': 'path/to/es.vtt'}
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate content object after initialization"""
        if not any([self.video_file, self.image_file, self.description]):
            raise ValueError("Content must have at least video, image, or description")

        # Validate file paths exist
        if self.video_file and not os.path.exists(self.video_file):
            raise FileNotFoundError(f"Video file not found: {self.video_file}")
        if self.image_file and not os.path.exists(self.image_file):
            raise FileNotFoundError(f"Image file not found: {self.image_file}")
        if self.subtitle_files:
            for lang, path in self.subtitle_files.items():
                if not os.path.exists(path):
                    raise FileNotFoundError(f"Subtitle file not found for {lang}: {path}")

    @staticmethod
    def of_dir(dir_path: str,
               title: str,
               content_orientation: str = "portrait",
               language_code: str = "en",
               tags: Union[List[str], bool] = False,
               accept_file: Callable[[str], bool] = lambda arg: True) -> 'Content':
        if not dir_path:
            raise ValueError("Directory path is required")
        if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
            raise ValueError(f"Invalid directory path: {dir_path}")

        text_file_names = [e for e in os.listdir(dir_path) if e.endswith(".txt") and accept_file(e)]

        text_file_name = Content.__determine_text_file_name(text_file_names, dir_path)

        with open(os.path.join(dir_path, text_file_name), 'r') as f:
            description = f.read()
            logger.debug(f"Description length {len(description)} chars")

        video_file = os.path.join(dir_path,  f"video-{content_orientation}.mp4")
        if not os.path.exists(video_file):
            video_file = os.path.join(dir_path, "video.mp4")

        image_file = os.path.join(dir_path, f"cover-{content_orientation}.jpg")
        if not os.path.exists(image_file):
            image_file = os.path.join(dir_path, f"cover-{content_orientation}.jpeg")
            if not os.path.exists(image_file):
                image_file = os.path.join(dir_path, "cover.jpg")
                if not os.path.exists(image_file):
                    image_file = os.path.join(dir_path, "cover.jpeg")

        if not title and len(text_file_names) == 2:
            title = [e for e in text_file_names if e != text_file_name][0]

        if not title:
            name = os.path.basename(dir_path).replace("-", " ").replace("   ", " - ")
            title = f"{name[0].upper()}{name[1:]}"

        def is_valid_lang_code(code) -> bool:
            return (len(code) == 2 and code.isalpha()) or (len(code) == 5 and code[2] == '-' and code[:2].isalpha() and code[3:].isalpha())

        subtitles_dir_path = f"{dir_path}/subtitles"
        logger.debug(f"Checking subtitles directory: {subtitles_dir_path}")
        subtitle_files = {}
        if os.path.exists(subtitles_dir_path):
            for file_name in os.listdir(subtitles_dir_path):
                if file_name.endswith('.srt') or file_name.endswith('.vtt'):
                    lang_code = file_name.split('.')[-2]
                    if not is_valid_lang_code(lang_code):
                        logger.debug(f"Skipping invalid lang code: {lang_code} for file path: {file_name}")
                        continue
                    subtitle_files[lang_code] = os.path.join(subtitles_dir_path, file_name)
                    logger.debug(f"Found subtitle file for {lang_code}={file_name}")

        if tags is True:
            tags = Content.extract_hashtags_from_text(description, 500)
            logger.debug(f"Extracted tags from description: {tags}")

        return Content(
            description=description,
            video_file=video_file if os.path.exists(video_file) else None,
            image_file=image_file if os.path.exists(image_file) else None,
            title=title,
            subtitle_files=subtitle_files,
            language_code=language_code,
            tags=tags
        )

    @staticmethod
    def __determine_text_file_name(text_file_names: list, dir_path) -> str:
        if not text_file_names:
            raise ValueError(f"No .txt file found in directory: {dir_path}")

        if len(text_file_names) == 1:
            return text_file_names[0]
        if 'video-description.txt' in text_file_names:
            return "video-description.txt"
        if 'description.txt' in text_file_names:
            return "description.txt"
        if 'video-content.txt' in text_file_names:
            return "video-content.txt"
        if 'video.txt' in text_file_names:
            return "video.txt"
        if 'content.txt' in text_file_names:
            return "content.txt"
        raise ValueError(f"Multiple .txt files found in directory: {dir_path}. Please "
                         f"ensure only one description file is present or name one as "
                         f"'video-description.txt' or 'description.txt'.")

    @staticmethod
    def extract_hashtags_from_text(text: str, max_tags_length: int) -> list[str]:
        import re
        hashtags = re.findall(r'#\w+', text)
        all_tags = [tag.lstrip('#') for tag in hashtags]
        total_len = 0
        result = []
        for tag in all_tags:
            tag_len = len(tag) + (1 if result else 0) # add one for comma
            if total_len + tag_len > max_tags_length:
                break
            result.append(tag)
            total_len += tag_len
        return result

@dataclass
class PostRequest:
    """Request object containing platform and content information"""
    api_config: SocialPlatformApiConfig
    content: Content

    def __post_init__(self):
        """Validate request object"""
        if not self.api_config.platform_name:
            raise ValueError("Platform name is required")
        if not self.api_config.api_credentials:
            raise ValueError("API credentials are required")

@dataclass
class PostResult:
    """Result object returned after posting attempt"""
    success: bool = False
    message: str = ""
    steps_log: List[str] = field(default_factory=list)
    platform_response: Optional[Dict[str, Any]] = None
    post_url: Optional[str] = None

    def add_step(self, step: str, log_level = logging.INFO) -> 'PostResult':
        """Add a step to the execution log"""
        self.steps_log.append(f"{datetime.now().strftime('%H:%M:%S')} - {step}")
        logger.log(log_level, step)
        return self

    def as_auth_failure(self) -> 'PostResult':
        return self.as_failure("Authentication failed")

    def as_failure_ex(self, message: str, ex: Exception) -> 'PostResult':
        logger.exception(message, exc_info=ex)
        return self.as_failure(message)

    def as_failure(self, message: str) -> 'PostResult':
        self.success = False
        self.add_step(message, logging.WARNING)
        self.message = message
        return self

    def as_success(self, message: str) -> 'PostResult':
        self.success = True
        self.add_step(message, logging.DEBUG)
        self.message = message
        return self

    def __str__(self):
        steps_lines = '\n'.join(self.steps_log)
        return (f"{self.__class__.__name__}"
                f"(success={self.success}\nmessage={self.message}\npost_url={self.post_url}"
                f"\nsteps_log={steps_lines})")

class SocialContentPublisher(ABC):
    """Abstract base class for social media publishers"""

    def __init__(self, api_endpoint: str, credentials: Dict[str, Any],
                 supported_post_types: List[PostType] = List[PostType]):
        self.api_endpoint = api_endpoint
        self.credentials = credentials
        self.supports_subtitles = False
        self.supported_post_types = supported_post_types

    @abstractmethod
    def _authenticate(self) -> bool:
        """Authenticate with the platform API"""
        pass

    @abstractmethod
    def post_content(self, content: Content, result: Optional[PostResult] = None) -> PostResult:
        """Post content to the platform"""
        pass

    def validate_content(self, content: Content, result: Optional[PostResult] = None) -> PostResult:
        """Validate content for the specific platform"""
        if result is None:
            result = PostResult()

        result.add_step("Validating content for platform")

        # Check if platform supports the media types
        if content.video_file and PostType.VIDEO not in self.supported_post_types:
            return result.as_failure("Platform does not support video content")

        if content.image_file and PostType.IMAGE not in self.supported_post_types:
            return result.as_failure("Platform does not support image content")

        return result.as_success("Content validation passed")


class SocialContentPublisherFactory:
    def __init__(self):

        from .google.youtube_content_publisher import YouTubeContentPublisher
        from .meta.facebook_content_publisher import FacebookContentPublisher
        from .reddit.reddit_content_publisher import RedditContentPublisher
        from .tiktok.tiktok_content_publisher import TikTokContentPublisher
        from .x.x_content_publisher import XContentPublisher

        self.publishers = {
            SocialPlatformType.FACEBOOK.value: FacebookContentPublisher,
            SocialPlatformType.META.value: FacebookContentPublisher,
            SocialPlatformType.REDDIT.value: RedditContentPublisher,
            SocialPlatformType.TIKTOK.value: TikTokContentPublisher,
            SocialPlatformType.TWITTER.value: XContentPublisher,
            SocialPlatformType.X.value: XContentPublisher,
            SocialPlatformType.YOUTUBE.value: YouTubeContentPublisher
        }

    def get_publisher(self, api_config: SocialPlatformApiConfig) -> Optional[SocialContentPublisher]:
        publisher_class = self.publishers.get(api_config.platform_name)
        if not publisher_class:
            return None
        return publisher_class(api_config.api_endpoint, api_config.api_credentials)

class SocialMediaPoster:
    """Main class for posting content to social media platforms"""

    def __init__(self, publisher_factory: SocialContentPublisherFactory = SocialContentPublisherFactory()):
        self.__publisher_factory = publisher_factory

    def post_content(self, request: PostRequest) -> PostResult:
        """
        Main method to post content to specified social media platform

        Args:
            request: PostRequest object containing platform and content info

        Returns:
            PostResult object with success/failure status and detailed logs
        """
        result = PostResult()

        try:
            platform = request.api_config.platform_name
            
            result.add_step(f"Starting content posting process for platform: {platform}")

            publisher = self.__publisher_factory.get_publisher(request.api_config)
            if not publisher:
                return result.as_failure(f"Unsupported platform: {platform}")

            result.add_step(f"Selected publisher: {publisher.__class__.__name__}, for platform: {platform}")

            result = publisher.validate_content(request.content, result)
            if not result.success:
                return result

            return publisher.post_content(request.content, result)

        except Exception as ex:
            return result.as_failure(f"Unexpected error: {str(ex)}")