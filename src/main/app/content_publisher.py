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
from typing import Dict, List, Any, Optional, Callable
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
    subtitle_files: Optional[Dict[str, str]] = None  # {'en': 'path/to/en.srt', 'es': 'path/to/es.vtt'}

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
               accept_file: Callable[[str], bool] = lambda arg: True) -> 'Content':
        if not dir_path:
            raise ValueError("Directory path is required")
        if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
            raise ValueError(f"Invalid directory path: {dir_path}")

        text_file_names = [e for e in os.listdir(dir_path) if e.endswith(".txt") and accept_file(e)]
        if not text_file_names:
            raise ValueError(f"No .txt file found in directory: {dir_path}")

        if len(text_file_names) == 1:
            text_file_name = text_file_names[0]
        elif 'video-description.txt' in text_file_names:
            text_file_name = "video-description.txt"
        elif 'description.txt' in text_file_names:
            text_file_name = "description.txt"
        elif 'video-content.txt' in text_file_names:
            text_file_name = "video-content.txt"
        elif 'video.txt' in text_file_names:
            text_file_name = "video.txt"
        elif 'content.txt' in text_file_names:
            text_file_name = "content.txt"
        else:
            raise ValueError(f"Multiple .txt files found in directory: {dir_path}. Please ensure only one description file is present or name one as 'video-description.txt' or 'description.txt'.")

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

        return Content(
            description=description,
            video_file=video_file if os.path.exists(video_file) else None,
            image_file=image_file if os.path.exists(image_file) else None,
            title=title,
            subtitle_files=subtitle_files
        )

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
    def post_content(self, content: Content, result: Optional[PostResult] = None) -> PostResult:
        """Post content to the platform"""
        pass

    def validate_content(self, content: Content, result: Optional[PostResult] = None) -> PostResult:
        """Validate content for the specific platform"""
        if result is None:
            result = PostResult()

        result.add_step("Validating content for platform")

        # Check if platform supports the media types
        if content.video_file and 'video' not in self.supported_media_types:
            return result.as_failure("Platform does not support video content")

        if content.image_file and 'image' not in self.supported_media_types:
            return result.as_failure("Platform does not support image content")

        return result.as_success("Content validation passed")

    def add_subtitles(self, subtitle_files: Dict[str, str], video_id: str, result: Optional[PostResult] = None) -> PostResult:
        """Add subtitles to posted content if supported"""
        return result.as_failure("Subtitle addition not implemented")

class YouTubeContentPublisher(SocialContentPublisher):
    """Handler for YouTube API"""

    def __init__(self, api_endpoint: str, credentials: Dict[str, Any]):
        super().__init__(api_endpoint, credentials)
        self.__version = api_endpoint.split("/")[-1]
        self.supports_subtitles = True
        # TODO Support adding cover image
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

    def post_content(self, content: Content, result: Optional[PostResult] = None) -> PostResult:
        """Post video content to YouTube"""
        if result is None:
            result = PostResult()
        try:
            if not self.authenticate():
                return result.as_failure("Authentication failed")

            result.add_step("Authenticated with YouTube API")

            if not content.video_file:
                return result.as_failure("YouTube requires a video file")

            # Prepare video metadata
            body = {
                'snippet': {
                    'title': content.title or 'Untitled Video',
                    'description': content.description,
                    'categoryId': 22 # People & Blogs
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
                self.add_subtitles(content.subtitle_files, video_id, result)

            if not result.success:
                return result
            
            return result.as_success("Video posted successfully to YouTube")

        except Exception as ex:
            return result.as_failure(f"Failed to post to YouTube: {str(ex)}")

    def add_subtitles(self, subtitle_files: Dict[str, str], video_id: str, result: Optional[PostResult] = None) -> PostResult:
        """Add subtitles to YouTube video"""
        if result is None:
            result = PostResult()
        try:
            if not self.supports_subtitles or not subtitle_files:
                message = "Adding of subtitles is not supported"
                return result.as_failure(message)

            for language, subtitle_file in subtitle_files.items():
                media = MediaFileUpload(subtitle_file)

                insert_request = self.service.captions().insert(
                    part='snippet',
                    body={
                        'snippet': {
                            'videoId': video_id,
                            'language': language,
                            'name': f'Subtitles ({language})',
                            'isDraft': False
                        }
                    },
                    media_body=media
                )

                insert_request.execute()
                result.add_step(f"Added subtitles for language: {language}")

            return result
        except Exception as ex:
            message = f"Failed to add subtitles: {str(ex)}"
            return result.as_failure(message)

    @staticmethod
    def _get_youtube_credentials_interactively(client_id: str, client_secret: str) -> Dict[str, str]:
        generator = GoogleOAuthTokenGenerator(client_id, client_secret)

        # We need permission 'youtube.force-ssl' to upload subtitles
        scopes = generator.to_scopes(['youtube', 'youtube.force-ssl'])
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

    def post_content(self, content: Content, result: Optional[PostResult] = None) -> PostResult:
        """Post content to Facebook"""
        if result is None:
            result = PostResult()
        try:
            if not self.authenticate():
                return result.as_failure("Authentication failed")

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
            return result.as_success("Content posted successfully to Facebook")

        except Exception as ex:
            return result.as_failure(f"Failed to post to Facebook: {str(ex)}")

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

    def post_content(self, content: Content, result: Optional[PostResult] = None) -> PostResult:
        """Post content to Twitter/X"""
        if result is None:
            result = PostResult()
        try:
            if not self.authenticate():
                return result.as_failure("Authentication failed")

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
            return result.as_success("Content posted successfully to Twitter")

        except Exception as ex:
            return result.as_failure(f"Failed to post to Twitter: {str(ex)}")

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

    def post_content(self, content: Content, result: Optional[PostResult] = None) -> PostResult:
        """Post content to Reddit"""
        if result is None:
            result = PostResult()
        try:
            if not self.authenticate():
                return result.as_failure("Authentication failed")

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
            return result.as_success("Content posted successfully to Reddit")

        except Exception as ex:
            return result.as_failure(f"Failed to post to Reddit: {str(ex)}")

class SocialContentPublisherFactory:
    def __init__(self):
        self.publishers = {
            SocialPlatformType.YOUTUBE.value: YouTubeContentPublisher,
            SocialPlatformType.FACEBOOK.value: FacebookContentPublisher,
            SocialPlatformType.META.value: FacebookContentPublisher,
            SocialPlatformType.X.value: XHandler,
            SocialPlatformType.REDDIT.value: RedditContentPublisher
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
