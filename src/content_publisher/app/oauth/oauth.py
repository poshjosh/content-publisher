import base64
import logging
import secrets

from abc import ABC, abstractmethod
from typing import Any, Optional

from .credentials import Credentials, CredentialsStore
from .oauth_callback_handler import OAuthCallbackHandler
from .oauth_flow import OAuthFlow

logger = logging.getLogger(__name__)


class OAuth(ABC):
    def __init__(self, config: dict[str, Any]):
        self.__callback_path = config.get("callback_path")
        self.credentials_store = CredentialsStore()

    @abstractmethod
    def _build_auth_url(self, scopes: list[str], additional_params: Optional[dict[str, Any]] = None) -> str:
        raise NotImplementedError

    @abstractmethod
    def _exchange_auth_code_for_access_token(self,
                                             authorization_code: str,
                                             additional_params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def _refresh_access_token(self, refresh_token: str) -> Optional[dict[str, Any]]:
        raise NotImplementedError

    def get_credentials_interactively(self, scopes: list[str], credentials_file: Optional[str] = None) -> Credentials:

        callback_path = self.__callback_path

        class OAuthCallbackHandlerWithState(OAuthCallbackHandler):
            def get_callback_path(self) -> Optional[str]:
                return callback_path

        def get_auth_code() -> str:
            auth_url = self._build_auth_url(scopes)
            return self.prompt_user_to_authorize_app(auth_url, OAuthCallbackHandlerWithState)

        def fetch_credentials(credentials: Optional[Credentials]):
            if credentials and credentials.is_expired() and credentials.is_refreshable():
                token_data = self._refresh_access_token(credentials.refresh_token)
                if token_data:
                    return Credentials(token_data).with_scopes(scopes)

            token_data = self._exchange_auth_code_for_access_token(get_auth_code())
            return Credentials(token_data).with_scopes(scopes)

        if not credentials_file:
            return fetch_credentials(None)

        return self.credentials_store.load_or_fetch(fetch_credentials, credentials_file, scopes)

    def prompt_user_to_authorize_app(self, auth_url: str, callback_handler, timeout: int = 30) -> str:
        oauth_flow = OAuthFlow()
        try:
            oauth_flow.start_callback_server(callback_handler if callback_handler else OAuthCallbackHandler)
            oauth_flow.open_browser(auth_url)
            return oauth_flow.wait_for_authorization(timeout=timeout)
        finally:
            oauth_flow.stop_callback_server()

    @staticmethod
    def generate_csrf_token(length: int = 32) -> str:
        """
        Generate a cryptographically secure CSRF token suitable for OAuth state parameter.

        Args:
            length (int): Number of random bytes to use before encoding. Default is 32.

        Returns:
            str: A URL-safe base64-encoded token string.
        """
        # Generate a secure random byte string
        random_bytes = secrets.token_bytes(length)

        # Encode it into a URL-safe base64 string (no '=' padding)
        return base64.urlsafe_b64encode(random_bytes).rstrip(b'=').decode('utf-8')