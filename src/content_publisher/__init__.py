"""
A Python app for publishing content to social media
"""
from .app.app import App
from .app.config import ConfigFactory, PublisherConfig, SocialPlatformType
from .app.content_publisher import Content, PostType, PostRequest, PostResult, \
    SocialContentPublisher, SocialMediaPoster, SocialPlatformApiConfig

__all__ = ["App", "ConfigFactory", "PublisherConfig", "Content", "PostType", "PostRequest",
           "PostResult", "SocialContentPublisher", "SocialMediaPoster", "SocialPlatformApiConfig",
           "SocialPlatformType"]