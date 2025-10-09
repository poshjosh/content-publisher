"""
A Python app for publishing content to social media
"""

__version__ = "0.2.0"
__author__ = "https://github.com/poshjosh"

from .app.app import App
from .app.config import Config
from .app.content_publisher import Content, PostType, PostRequest, PostResult, \
    SocialContentPublisher, SocialMediaPoster, SocialPlatformApiConfig, SocialPlatformType

__all__ = ["App", "Config", "Content", "PostType", "PostRequest", "PostResult",
           "SocialContentPublisher", "SocialMediaPoster", "SocialPlatformApiConfig",
           "SocialPlatformType"]