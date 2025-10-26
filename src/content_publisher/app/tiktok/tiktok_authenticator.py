import requests
import time
from typing import Optional, Dict
import logging

from content_publisher.app.credentials import Credentials
from content_publisher.app.tiktok.tiktok import TikTokAPIError

logger = logging.getLogger(__name__)


class TikTokAuthenticationError(TikTokAPIError):
    """Exception raised for authentication failures"""
    pass


class TikTokAuthenticator:
    """Handles TikTok API authentication"""

    def __init__(self, api_endpoint: str, credentials: Dict[str, str]):
        """
        Initialize authenticator

        Args:
            api_endpoint: TikTok API base URL
            credentials: Dict containing 'client_key' and 'client_secret'
        """
        self.api_endpoint = api_endpoint.rstrip('/')
        self.credentials = credentials

        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expires_at: Optional[float] = None
        logger.debug("TikTok Authenticator initialized")

    def set_credentials(self, credentials: Credentials):
        self.access_token = credentials.access_token
        self.refresh_token = credentials.data.get('refresh_token')
        self.token_expires_at = credentials.data.get('expires_at')

    def get_credentials(self, scopes: list[str]) -> Optional[Dict[str, str]]:
        """Return current credentials including tokens"""
        if self.access_token and self.refresh_token:
            return {
                "access_token": self.access_token,
                "refresh_token": self.refresh_token,
                "expires_at": self.token_expires_at,
                "scopes": scopes
            }
        return None

    def get_access_token(self, authorization_code: str, code_verifier: Optional[str]) -> str:
        """
        Exchange authorization code for access token

        Args:
            authorization_code: Authorization code from OAuth flow
            code_verifier: Code verifier for PKCE, if applicable

        Returns:
            Access token string

        Raises:
            TikTokAuthenticationError: If authentication fails
        """
        url = f"{self.api_endpoint}/oauth/token/"

        headers = { "Content-Type": "application/x-www-form-urlencoded" }

        payload = {
            **self.credentials,
            "code": authorization_code,
            "grant_type": "authorization_code"
        }

        if code_verifier:
            payload["code_verifier"] = code_verifier

        try:
            logger.debug("Requesting access token...")
            response = requests.post(url, headers=headers, data=payload, timeout=30)
            response.raise_for_status()

            response_data = response.json()

            if 'access_token' in response_data:
                self.access_token = response_data.get('access_token')
                self.refresh_token = response_data.get('refresh_token')
                expires_in = response_data.get('expires_in', 3600)
                self.token_expires_at = time.time() + expires_in

                logger.debug("Access token obtained successfully")
                return self.access_token
            else:
                raise TikTokAuthenticationError(f"Failed to get access token: {response_data}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Authentication request failed: {e}")
            raise TikTokAuthenticationError(f"Authentication request failed: {e}")

    def refresh_access_token(self) -> str:
        """
        Refresh access token using refresh token

        Returns:
            New access token string

        Raises:
            TikTokAuthenticationError: If refresh fails
        """
        if not self.refresh_token:
            raise TikTokAuthenticationError("No refresh token available")

        url = f"{self.api_endpoint}/oauth/token/"

        headers = { "Content-Type": "application/x-www-form-urlencoded" }

        payload = {
            "client_key": self.credentials["client_key"],
            "client_secret": self.credentials["client_secret"],
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token
        }

        try:
            logger.debug("Refreshing access token...")
            response = requests.post(url, headers=headers, data=payload, timeout=30)
            response.raise_for_status()

            response_data = response.json()

            if 'access_token' in response_data:
                self.access_token = response_data.get('access_token')
                self.refresh_token = response_data.get('refresh_token')
                expires_in = response_data.get('expires_in', 3600)
                self.token_expires_at = time.time() + expires_in

                logger.debug("Access token refreshed successfully")
                return self.access_token
            else:
                raise TikTokAuthenticationError(f"Failed to refresh token: {response_data}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Token refresh request failed: {e}")
            raise TikTokAuthenticationError(f"Token refresh request failed: {e}")

    def is_token_expired(self) -> bool:
        """Check if access token is expired"""
        if not self.token_expires_at:
            return True
        # Add 60 second buffer
        return time.time() >= (self.token_expires_at - 60)

    def ensure_valid_token(self) -> str:
        """
        Ensure we have a valid access token, refresh if needed

        Returns:
            Valid access token

        Raises:
            TikTokAuthenticationError: If unable to get valid token
        """
        if not self.access_token:
            raise TikTokAuthenticationError("No access token available. Call get_access_token() first.")

        if self.is_token_expired():
            logger.debug("Token expired, refreshing...")
            return self.refresh_access_token()

        return self.access_token