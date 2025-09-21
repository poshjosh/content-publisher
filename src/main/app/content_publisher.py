#!/usr/bin/env python3
"""
Social Media Content Posting System

A comprehensive system for posting content to multiple social media platforms
with support for videos, images, text, and subtitles where supported.

Supported platforms: YouTube, Facebook/Meta, Instagram, X (Twitter), Reddit
Note: TikTok does not have a public API and is not supported.
"""

import os
import logging

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

# YouTube API
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

# Facebook/Meta API
import facebook

# Twitter/X API
import tweepy

# Reddit API
import praw

from .google.google_oauth_token_generator import GoogleOAuthTokenGenerator

logger = logging.getLogger(__name__)

class SocialPlatformType(Enum):
    """Supported social media platforms"""
    YOUTUBE = "youtube"
    FACEBOOK = "facebook"
    META = "meta"  # Alias for Facebook
    INSTAGRAM = "instagram"
    X = "x"
    REDDIT = "reddit"
    TIKTOK = "tiktok"

@dataclass
class ContentObject:
    """Content object containing all media and metadata"""
    description: str
    video_file: Optional[str] = None
    image_file: Optional[str] = None
    title: Optional[str] = None
    subtitle_files: Optional[Dict[str, str]] = None  # {'en': 'path/to/en.srt', 'es': 'path/to/es.srt'}

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

@dataclass
class SocialMediaRequest:
    """Request object containing platform and content information"""
    platform_name: str
    api_endpoint: str
    api_credentials: Dict[str, Any]
    content: ContentObject

    def __post_init__(self):
        """Validate request object"""
        if not self.platform_name:
            raise ValueError("Platform name is required")
        if not self.api_credentials:
            raise ValueError("API credentials are required")

@dataclass
class PostResult:
    """Result object returned after posting attempt"""
    success: bool = False
    message: str = ""
    steps_log: List[str] = field(default_factory=list)
    platform_response: Optional[Dict[str, Any]] = None
    post_url: Optional[str] = None
    error_details: Optional[str] = None

    def add_step(self, step: str):
        """Add a step to the execution log"""
        self.steps_log.append(f"{datetime.now().strftime('%H:%M:%S')} - {step}")
        logger.info(step)

    def __str__(self):
        return (f"{self.__class__.__name__}"
                f"(success={self.success}\nmessage={self.message}\npost_url={self.post_url}"
                f"\nsteps_log={self.steps_log}\nerror_details={self.error_details})")


class SocialContentPublisher(ABC):
    """Abstract base class for social media handlers"""

    def __init__(self, api_endpoint: str, credentials: Dict[str, Any]):
        self.api_endpoint = api_endpoint
        self.credentials = credentials
        self.supports_subtitles = False
        self.supported_media_types = []

    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the platform API"""
        pass

    @abstractmethod
    def post_content(self, content: ContentObject, result: PostResult) -> PostResult:
        """Post content to the platform"""
        pass

    def validate_content(self, content: ContentObject, result: PostResult) -> bool:
        """Validate content for the specific platform"""
        result.add_step("Validating content for platform")

        # Check if platform supports the media types
        if content.video_file and 'video' not in self.supported_media_types:
            result.message = "Platform does not support video content"
            return False

        if content.image_file and 'image' not in self.supported_media_types:
            result.message = "Platform does not support image content"
            return False

        result.add_step("Content validation passed")
        return True

    def add_subtitles(self, content: ContentObject, post_id: str, result: PostResult) -> bool:
        """Add subtitles to posted content if supported"""
        if not self.supports_subtitles or not content.subtitle_files:
            return True

        result.add_step("Adding subtitles (not implemented in base class)")
        return True

class YouTubeContentPublisher(SocialContentPublisher):
    """Handler for YouTube API"""

    def __init__(self, api_endpoint: str, credentials: Dict[str, Any]):
        super().__init__(api_endpoint, credentials)
        self.__version = api_endpoint.split("/")[-1]
        self.supports_subtitles = True
        self.supported_media_types = ['video']
        self.service = None

    def authenticate(self) -> bool:
        """Authenticate with YouTube API"""
        try:
            # Assuming credentials contain OAuth token or service account info
            if 'oauth_token' in self.credentials:
                creds = Credentials(token=self.credentials['oauth_token'])
                self.service = build('youtube', self.__version, credentials=creds)
            elif 'client_id' in self.credentials and 'client_secret' in self.credentials:
                creds_dict = self._get_youtube_credentials_interactively(self.credentials['client_id'], self.credentials['client_secret'])
                creds = Credentials(token=creds_dict['oauth_token'], refresh_token=creds_dict.get('refresh_token'))
                self.service = build('youtube', self.__version, credentials=creds)
            else:
                # Alternative: use API key for read-only operations
                self.service = build('youtube', self.__version, developerKey=self.credentials.get('api_key'))
            return True
        except Exception as ex:
            logger.error(f"YouTube authentication failed: {ex}")
            return False

    def post_content(self, content: ContentObject, result: PostResult) -> PostResult:
        """Post video content to YouTube"""
        try:
            if not self.authenticate():
                result.message = "Authentication failed"
                return result

            result.add_step("Authenticated with YouTube API")

            if not content.video_file:
                result.message = "YouTube requires a video file"
                return result

            # Prepare video metadata
            body = {
                'snippet': {
                    'title': content.title or 'Untitled Video',
                    'description': content.description,
                    'categoryId': '22'  # People & Blogs
                },
                'status': {
                    'privacyStatus': 'public',
                    'selfDeclaredMadeForKids': False
                }
            }

            # Create media upload object
            media = MediaFileUpload(
                content.video_file,
                chunksize=-1,
                resumable=True
            )

            result.add_step("Prepared video upload")

            # Upload video
            insert_request = self.service.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )

            response = insert_request.execute()
            video_id = response['id']

            result.add_step(f"Video uploaded successfully - ID: {video_id}")
            result.post_url = f"https://www.youtube.com/watch?v={video_id}"
            result.platform_response = response

            # Add subtitles if provided
            if content.subtitle_files:
                self.add_subtitles(content, video_id, result)

            result.success = True
            result.message = "Video posted successfully to YouTube"
            return result

        except Exception as ex:
            result.message = f"Failed to post to YouTube: {str(ex)}"
            result.error_details = str(ex)
            return result

    def add_subtitles(self, content: ContentObject, video_id: str, result: PostResult) -> bool:
        """Add subtitles to YouTube video"""
        try:
            for language, subtitle_file in content.subtitle_files.items():
                media = MediaFileUpload(subtitle_file)

                insert_request = self.service.captions().insert(
                    part='snippet',
                    body={
                        'snippet': {
                            'videoId': video_id,
                            'language': language,
                            'name': f'Subtitles ({language})'
                        }
                    },
                    media_body=media
                )

                insert_request.execute()
                result.add_step(f"Added subtitles for language: {language}")

            return True
        except Exception as ex:
            result.add_step(f"Failed to add subtitles: {str(ex)}")
            return False

    @staticmethod
    def _get_youtube_credentials_interactively(client_id: str, client_secret: str) -> Dict[str, str]:
        generator = GoogleOAuthTokenGenerator(client_id, client_secret)

        # We need full to upload subtitles
        scopes = generator.get_common_scopes(['youtube_full'])
        tokens = generator.get_tokens_interactive(scopes, save_tokens=True)

        return {
            'oauth_token': tokens['access_token'],
            'refresh_token': tokens['refresh_token']
        }

class FacebookContentPublisher(SocialContentPublisher):
    """Handler for Facebook/Meta API"""

    def __init__(self, api_endpoint: str, credentials: Dict[str, Any]):
        super().__init__(api_endpoint, credentials)
        self.supports_subtitles = False
        self.supported_media_types = ['video', 'image', 'text']
        self.graph = None

    def authenticate(self) -> bool:
        """Authenticate with Facebook Graph API"""
        try:
            access_token = self.credentials.get('access_token')
            if not access_token:
                return False

            self.graph = facebook.GraphAPI(access_token=access_token)
            # Test the connection
            self.graph.get_object('me')
            return True
        except Exception as ex:
            logger.error(f"Facebook authentication failed: {ex}")
            return False

    def post_content(self, content: ContentObject, result: PostResult) -> PostResult:
        """Post content to Facebook"""
        try:
            if not self.authenticate():
                result.message = "Authentication failed"
                return result

            result.add_step("Authenticated with Facebook API")

            page_id = self.credentials.get('page_id', 'me')

            if content.video_file:
                # Post video
                with open(content.video_file, 'rb') as video_file:
                    response = self.graph.put_video(
                        video=video_file,
                        description=content.description,
                        title=content.title
                    )
            elif content.image_file:
                # Post photo
                with open(content.image_file, 'rb') as image_file:
                    response = self.graph.put_photo(
                        image=image_file,
                        message=content.description
                    )
            else:
                # Post text only
                response = self.graph.put_object(
                    parent_object=page_id,
                    connection_name='feed',
                    message=content.description
                )

            post_id = response.get('id') or response.get('post_id')
            result.add_step(f"Content posted successfully - ID: {post_id}")
            result.post_url = f"https://www.facebook.com/{post_id}"
            result.platform_response = response
            result.success = True
            result.message = "Content posted successfully to Facebook"
            return result

        except Exception as ex:
            result.message = f"Failed to post to Facebook: {str(ex)}"
            result.error_details = str(ex)
            return result

class XHandler(SocialContentPublisher):
    """Handler for X (Twitter) API"""

    def __init__(self, api_endpoint: str, credentials: Dict[str, Any]):
        super().__init__(api_endpoint, credentials)
        self.supports_subtitles = False
        self.supported_media_types = ['image', 'text', 'video']
        self.api = None

    def authenticate(self) -> bool:
        """Authenticate with Twitter API"""
        try:
            auth = tweepy.OAuth1UserHandler(
                consumer_key=self.credentials['consumer_key'],
                consumer_secret=self.credentials['consumer_secret'],
                access_token=self.credentials['access_token'],
                access_token_secret=self.credentials['access_token_secret']
            )

            self.api = tweepy.API(auth)
            # Test authentication
            self.api.verify_credentials()
            return True
        except Exception as ex:
            logger.error(f"Twitter authentication failed: {ex}")
            return False

    def post_content(self, content: ContentObject, result: PostResult) -> PostResult:
        """Post content to Twitter/X"""
        try:
            if not self.authenticate():
                result.message = "Authentication failed"
                return result

            result.add_step("Authenticated with Twitter API")

            media_ids = []

            # Upload media if present
            if content.image_file:
                media = self.api.media_upload(content.image_file)
                media_ids.append(media.media_id)
                result.add_step("Image uploaded")

            if content.video_file:
                media = self.api.media_upload(content.video_file)
                media_ids.append(media.media_id)
                result.add_step("Video uploaded")

            # Post tweet
            tweet_text = content.description[:280]  # Twitter character limit
            if content.title:
                tweet_text = f"{content.title}\n\n{content.description}"[:280]

            tweet = self.api.update_status(
                status=tweet_text,
                media_ids=media_ids if media_ids else None
            )

            result.add_step(f"Tweet posted successfully - ID: {tweet.id}")
            result.post_url = f"https://twitter.com/user/status/{tweet.id}"
            result.platform_response = tweet._json
            result.success = True
            result.message = "Content posted successfully to Twitter"
            return result

        except Exception as ex:
            result.message = f"Failed to post to Twitter: {str(ex)}"
            result.error_details = str(ex)
            return result

class RedditContentPublisher(SocialContentPublisher):
    """Handler for Reddit API"""

    def __init__(self, api_endpoint: str, credentials: Dict[str, Any]):
        super().__init__(api_endpoint, credentials)
        self.supports_subtitles = False
        self.supported_media_types = ['image', 'text', 'video']
        self.reddit = None

    def authenticate(self) -> bool:
        """Authenticate with Reddit API"""
        try:
            self.reddit = praw.Reddit(
                client_id=self.credentials['client_id'],
                client_secret=self.credentials['client_secret'],
                user_agent=self.credentials.get('user_agent', 'Social Media Poster'),
                username=self.credentials['username'],
                password=self.credentials['password']
            )

            # Test authentication
            self.reddit.user.me()
            return True
        except Exception as ex:
            logger.error(f"Reddit authentication failed: {ex}")
            return False

    def post_content(self, content: ContentObject, result: PostResult) -> PostResult:
        """Post content to Reddit"""
        try:
            if not self.authenticate():
                result.message = "Authentication failed"
                return result

            result.add_step("Authenticated with Reddit API")

            subreddit_name = self.credentials.get('subreddit', 'test')
            subreddit = self.reddit.subreddit(subreddit_name)

            title = content.title or content.description[:100]

            if content.image_file or content.video_file:
                # Submit media post
                media_file = content.image_file or content.video_file
                submission = subreddit.submit_image(
                    title=title,
                    image_path=media_file
                )
            else:
                # Submit text post
                submission = subreddit.submit(
                    title=title,
                    selftext=content.description
                )

            result.add_step(f"Post submitted successfully - ID: {submission.id}")
            result.post_url = submission.url
            result.platform_response = {'id': submission.id, 'url': submission.url}
            result.success = True
            result.message = "Content posted successfully to Reddit"
            return result

        except Exception as ex:
            result.message = f"Failed to post to Reddit: {str(ex)}"
            result.error_details = str(ex)
            return result

class SocialMediaPoster:
    """Main class for posting content to social media platforms"""

    def __init__(self):
        self.handlers = {
            SocialPlatformType.YOUTUBE.value: YouTubeContentPublisher,
            SocialPlatformType.FACEBOOK.value: FacebookContentPublisher,
            SocialPlatformType.META.value: FacebookContentPublisher,
            SocialPlatformType.X.value: XHandler,
            SocialPlatformType.REDDIT.value: RedditContentPublisher
        }

    def post_content(self, request: SocialMediaRequest) -> PostResult:
        """
        Main method to post content to specified social media platform

        Args:
            request: SocialMediaRequest object containing platform and content info

        Returns:
            PostResult object with success/failure status and detailed logs
        """
        result = PostResult()
        platform_name = request.platform_name.lower()

        try:
            result.add_step(f"Starting content posting process for platform: {platform_name}")

            # Get appropriate handler
            if platform_name not in self.handlers:
                result.message = f"Unsupported platform: {platform_name}"
                result.add_step(f"No handler found for platform: {platform_name}")
                return result

            handler_class = self.handlers[platform_name]
            handler = handler_class(request.api_endpoint, request.api_credentials)

            result.add_step(f"Selected handler for {platform_name}")

            # Validate content
            if not handler.validate_content(request.content, result):
                return result

            # Post content
            result = handler.post_content(request.content, result)

            return result

        except Exception as ex:
            result.message = f"Unexpected error: {str(ex)}"
            result.error_details = str(ex)
            result.add_step(f"Error occurred: {str(ex)}")
            return result