"""
TikTok OAuth 2.0 Implementation

Reference:
- https://developers.tiktok.com/doc/oauth-user-access-token-management
- https://developers.tiktok.com/doc/login-kit-web-settings/
"""
import hashlib
import logging
import secrets

import requests
import urllib.parse
from typing import Any, Optional

from ..oauth import Credentials, OAuth, OAuthCallbackHandler

logger = logging.getLogger(__name__)


class TikTokOAuth(OAuth):
    __authorize_url = "https://www.tiktok.com/v2/auth/authorize/"

    def __init__(self, api_endpoint: str, config: dict[str, str]):
        super().__init__(config)
        self.__api_endpoint = api_endpoint
        self.__client_key = config['client_key']
        self.__client_secret = config['client_secret']
        self.__redirect_uri = config['redirect_uri']
        self.__callback_path = config.get('callback_path')

    def get_credentials_interactively(self, scopes: list[str], credentials_file: Optional[str] = None) -> Credentials:
        callback_path = self.__callback_path
        code_verifier, code_challenge = TikTokOAuth.generate_code_challenge_pair()
        challenge_params = { "code_challenge": code_challenge }
        verifier_params = { "code_verifier": code_verifier }

        class TikTokOAuthCallbackHandler(OAuthCallbackHandler):
            def get_callback_path(self) -> Optional[str]:
                return callback_path

            def get_params_to_verify(self) -> Optional[dict[str,str]]:
                # TODO - Caused - Error code: 400, Message: Invalid/missing parameter: code_verifier
                # return verifier_params
                return None

        def get_auth_code() -> str:
            auth_url = self._build_auth_url(scopes, challenge_params)
            return self.prompt_user_to_authorize_app(auth_url, TikTokOAuthCallbackHandler)

        def fetch_credentials(credentials: Optional[Credentials]):
            if credentials and credentials.is_expired() and credentials.is_refreshable():
                logger.debug(f"Refreshing: {credentials}")
                token_data = self._refresh_access_token(credentials.refresh_token)
                credentials = Credentials(token_data).with_scopes(scopes) if token_data else None
                logger.debug(f"Refreshed: {credentials}")
                return credentials

            token_data = self._exchange_auth_code_for_access_token(get_auth_code(), verifier_params)
            credentials = Credentials(token_data).with_scopes(scopes)
            logger.debug(f"Fetched: {credentials}")
            return credentials

        if not credentials_file:
            return fetch_credentials(None)

        return self.credentials_store.load_or_fetch(credentials_file, fetch_credentials, scopes)

    def _build_auth_url(self, scopes: list[str], additional_params: Optional[dict[str, Any]] = None) -> str:
        params = {
            "client_key": self.__client_key,
            "client_secret": self.__client_secret,
            "response_type": "code",
            "scope": ",".join(scopes),
            "redirect_uri": self.__redirect_uri,
            "code_challenge_method": "S256"
        }

        if additional_params:
            params.update(additional_params)

        query_string = urllib.parse.urlencode(params)
        return f"{TikTokOAuth.__authorize_url}?{query_string}"

    def _exchange_auth_code_for_access_token(self,
                                             authorization_code: str,
                                             additional_params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        url = f"{self.__api_endpoint}/oauth/token/"

        headers = { "Content-Type": "application/x-www-form-urlencoded" }

        payload = {
            "client_key": self.__client_key,
            "client_secret": self.__client_secret,
            "redirect_uri": self.__redirect_uri,
            "code": authorization_code,
            "grant_type": "authorization_code"
        }

        if additional_params:
            payload.update(additional_params)

        logger.debug("Requesting access token...")
        response = requests.post(url, headers=headers, data=payload, timeout=30)
        self._log_response(response)
        response.raise_for_status()

        return response.json()

    def _refresh_access_token(self, refresh_token: str) -> Optional[dict[str, Any]]:
        """
        Refresh access token using refresh token

        Returns:
            New access token string
        """
        if not refresh_token:
            raise ValueError("No refresh token available")

        url = f"{self.__api_endpoint}/oauth/token/"

        headers = { "Content-Type": "application/x-www-form-urlencoded" }

        payload = {
            "client_key": self.__client_key,
            "client_secret": self.__client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }

        logger.debug("Refreshing access token...")
        response = requests.post(url, headers=headers, data=payload, timeout=30)
        self._log_response(response)
        response.raise_for_status()

        return response.json()

    @staticmethod
    def _log_response(response):
        try:
            logger.debug(f"Response json: {response.json()}")
        except Exception:
            logger.debug(f"Response: {response}")

    @staticmethod
    def generate_code_challenge_pair():
        random_str = TikTokOAuth._generate_random_string(60)
        sha256_hash = hashlib.sha256(random_str.encode('utf-8')).digest()
        code_challenge = sha256_hash.hex()  # Convert to hex string
        return random_str, code_challenge

    @staticmethod
    def _generate_random_string(length: int):
        characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~'
        return ''.join(secrets.choice(characters) for _ in range(length))
