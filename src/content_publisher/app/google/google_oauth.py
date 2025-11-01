#!/usr/bin/env python3
import os
import logging

from typing import Dict, List, Optional, Any
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials as GoogleCredentials
from google_auth_oauthlib.flow import Flow

from content_publisher.app.oauth import Credentials, CredentialsStore, OAuthFlow, \
    OAuthCallbackHandler

logger = logging.getLogger(__name__)


class GoogleOAuth:
    def __init__(self, config: dict[str, Any]):
        self.__client_id = config["client_id"]
        self.__callback_path = config.get("callback_path")
        self.__client_secret = config["client_secret"]
        self.__redirect_uri = 'http://localhost:8080'
        self.oauth_flow = OAuthFlow()
        self.credentials_store = CredentialsStore()

        if not self.__client_id or not self.__client_secret:
            raise ValueError("client_id and client_secret are required")

    def get_credentials_interactively(self, scopes: list[str], credentials_file: Optional[str] = None) -> Credentials:
        def fetch_credentials(credentials: Optional[Credentials]):
            if credentials and credentials.is_expired() and credentials.is_refreshable():
                google_creds = self.credentials_from_dict(credentials.data)
                google_creds.refresh(Request())
                token_data = self.credentials_to_dict(google_creds)
                return Credentials(token_data).with_scopes(scopes)

            token_data = self._get_credentials_interactively(scopes)
            return Credentials(token_data).with_scopes(scopes)

        if not credentials_file:
            return fetch_credentials(None)

        return self.credentials_store.load_or_fetch(fetch_credentials, credentials_file, scopes)

    def _get_credentials_interactively(self, scopes: List[str]) -> Dict[str, Any]:
        try:

            logger.debug("Starting interactive OAuth flow")

            client_config = self._create_client_config()
            flow = Flow.from_client_config(
                client_config,
                scopes=scopes,
                redirect_uri=self.__redirect_uri
            )

            callback_path = self.__callback_path
            class GoogleOAuthCallbackHandler(OAuthCallbackHandler):
                def get_callback_path(self) -> Optional[str]:
                    return callback_path

            self.oauth_flow.start_callback_server(GoogleOAuthCallbackHandler)

            flow.redirect_uri = self.__redirect_uri

            # Generate authorization URL
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'
            )

            self.oauth_flow.open_browser(auth_url)

            logger.debug("Waiting for OAuth callback...")
            self.oauth_flow.handle_request()

            auth_code = self.oauth_flow.wait_for_authorization(30)

            logger.debug("Exchanging authorization code for tokens")
            flow.fetch_token(code=auth_code)

            credentials = flow.credentials

            logger.debug("OAuth flow completed successfully")
            return self.credentials_to_dict(credentials)
        finally:
            self.oauth_flow.stop_callback_server()

    def get_credentials_headless(self, scopes: List[str], authorization_code: str) -> Dict[str, Any]:
        """
        Get OAuth tokens using authorization code (for headless/server environments)

        Args:
            scopes: List of OAuth scopes
            authorization_code: Authorization code obtained from OAuth flow

        Returns:
            Dictionary containing tokens
        """
        try:
            logger.debug("Starting headless OAuth token exchange")

            client_config = self._create_client_config()
            flow = Flow.from_client_config(
                client_config,
                scopes=scopes,
                redirect_uri='urn:ietf:wg:oauth:2.0:oob'  # Special redirect for headless
            )

            # Exchange authorization code for tokens
            flow.fetch_token(code=authorization_code)
            credentials = flow.credentials

            logger.debug("Token exchange completed successfully")
            return self.credentials_to_dict(credentials)

        except Exception as e:
            logger.error(f"Headless token exchange failed: {e}")
            raise

    def refresh_tokens(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh OAuth tokens using refresh token

        Args:
            refresh_token: Valid refresh token

        Returns:
            Dictionary containing new tokens
        """
        try:
            logger.debug("Refreshing OAuth tokens")

            credentials = GoogleCredentials(
                token=None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.__client_id,
                client_secret=self.__client_secret
            )

            credentials.refresh(Request())

            logger.debug("Token refresh completed successfully")
            return self.credentials_to_dict(credentials)

        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            raise

    def get_auth_url_headless(self, scopes: List[str], state: Optional[str] = None) -> str:
        """
        Generate authorization URL for manual OAuth flow

        Args:
            scopes: List of OAuth scopes
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL for user to visit
        """
        client_config = self._create_client_config()
        flow = Flow.from_client_config(
            client_config,
            scopes=scopes,
            redirect_uri='urn:ietf:wg:oauth:2.0:oob'
        )

        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',
            state=state
        )

        return auth_url

    def _create_client_config(self) -> Dict[str, Any]:
        """Create client configuration for OAuth flow"""
        return {
            "web": {
                "client_id": self.__client_id,
                "client_secret": self.__client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.__redirect_uri]
            }
        }

    @staticmethod
    def credentials_from_dict(data: Dict[str, Any]) -> GoogleCredentials:
        return GoogleCredentials(
            token=data.get('access_token'),
            refresh_token=data.get('refresh_token'),
            id_token=data.get('id_token'),
            token_uri=data.get('token_uri'),
            client_id=data.get('client_id'),
            client_secret=data.get('client_secret'),
            scopes=data.get('scopes'),
            granted_scopes=data.get('granted_scopes')
        )

    @staticmethod
    def credentials_to_dict(credentials: GoogleCredentials) -> Dict[str, Any]:
        """Convert Credentials object to dictionary"""
        return {
            'access_token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': list(credentials.scopes) if credentials.scopes else [],
            'expires_at': credentials.expiry.isoformat() if credentials.expiry else None,
            'valid': credentials.valid
        }

    @classmethod
    def to_scopes(cls, scope_names: List[str]) -> List[str]:
        """
        Get full scope URLs from common scope names

        Args:
            scope_names: List of scope names (e.g., ['youtube_full', 'drive_readonly'])

        Returns:
            List of full scope URLs
        """
        scope_url = 'https://www.googleapis.com/auth'
        scopes = []
        for scope_name in scope_names:
            if scope_name.startswith(scope_url):
                # Already a full scope URL
                scopes.append(scope_name)
            else:
                scopes.append(f"{scope_url}/{scope_name}")
        return scopes


def example():
    """
    Example usage and interactive CLI
    """
    print("Google OAuth Token Generator")
    print("=" * 40)

    # Get credentials from user or environment
    client_id = os.getenv('GOOGLE_CLIENT_ID') or input("Enter Google Client ID: ")
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET') or input("Enter Google Client Secret: ")

    config = {
        "client_id": client_id,
        "client_secret": client_secret
    }

    # Initialize generator
    oauth = GoogleOAuth(config)

    # Get desired scopes
    scope_input = input("\nEnter scopes (comma-separated names or full URLs): ")
    scope_names = [s.strip() for s in scope_input.split(',')]
    scopes = oauth.to_scopes(scope_names)

    print(f"\nRequesting scopes: {scopes}")

    # Choose flow type
    print("\nAvailable authentication methods:")
    print("1. Interactive (opens browser)")
    print("2. Manual (get authorization URL)")
    print("3. Refresh existing token")

    choice = input("Choose method (1-3): ")

    try:
        if choice == '1':
            # Interactive flow
            tokens = oauth.get_credentials_interactively(scopes).data
            print("\n" + "="*50)
            print("OAUTH TOKENS GENERATED SUCCESSFULLY")
            print("="*50)
            print(f"Access Token: {tokens['access_token']}")
            print(f"Refresh Token: {tokens['refresh_token']}")
            print(f"Expires At: {tokens['expires_at']}")
            print(f"Valid: {tokens['valid']}")

        elif choice == '2':
            # Manual flow
            auth_url = oauth.get_auth_url_headless(scopes)
            print("\nVisit this URL to authorize the application:")
            print(f"{auth_url}")
            print("\nAfter authorization, copy the authorization code and use it with:")
            print("generator.get_tokens_headless(scopes, authorization_code)")

        elif choice == '3':
            # Refresh token
            refresh_token = input("Enter refresh token: ")
            tokens = oauth.refresh_tokens(refresh_token)
            print("\n" + "="*50)
            print("TOKENS REFRESHED SUCCESSFULLY")
            print("="*50)
            print(f"New Access Token: {tokens['access_token']}")
            print(f"Expires At: {tokens['expires_at']}")

        else:
            print("Invalid choice")

    except Exception as e:
        print(f"\nError: {e}")
        logger.exception("OAuth process failed")

if __name__ == "__main__":
    print("\n" + "="*70)
    print("Google OAuth Token Generator")
    print("="*70)

    # Uncomment to run example:
    # example()