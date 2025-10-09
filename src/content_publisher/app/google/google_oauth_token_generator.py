#!/usr/bin/env python3
"""
Google OAuth Token Generator

This script generates OAuth access tokens for Google APIs using the OAuth 2.0 flow.
It can be used both as a standalone script and imported by other Python applications.

Dependencies:
    pip install google-auth google-auth-oauthlib google-auth-httplib2

Usage:
    As standalone script:
        python google_oauth.py

    As imported module:
        from google_oauth import GoogleOAuthTokenGenerator
        generator = GoogleOAuthTokenGenerator(client_id, client_secret)
        tokens = generator.get_tokens_interactively(scopes)
"""

import os
import pickle
import logging
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import parse_qs, urlparse
import webbrowser
import secrets
import hashlib
import base64

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

# HTTP server for OAuth callback
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler for OAuth callback"""

    def do_GET(self):
        """Handle GET request from OAuth callback"""
        self.server.auth_code = None
        self.server.auth_error = None

        # Parse query parameters
        query_params = parse_qs(urlparse(self.path).query)

        if 'code' in query_params:
            self.server.auth_code = query_params['code'][0]
            response = """
            <html>
                <head><title>Authentication Successful</title></head>
                <body>
                    <h1>Authentication Successful!</h1>
                    <p>You can close this window and return to your application.</p>
                </body>
            </html>
            """
            self.send_response(200)
        elif 'error' in query_params:
            self.server.auth_error = query_params['error'][0]
            response = f"""
            <html>
                <head><title>Authentication Failed</title></head>
                <body>
                    <h1>Authentication Failed</h1>
                    <p>Error: {self.server.auth_error}</p>
                    <p>Please close this window and try again.</p>
                </body>
            </html>
            """
            self.send_response(400)
        else:
            response = """
            <html>
                <head><title>Authentication Error</title></head>
                <body>
                    <h1>Authentication Error</h1>
                    <p>No authorization code received.</p>
                </body>
            </html>
            """
            self.send_response(400)

        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(response.encode())

    def log_message(self, format, *args):
        """Suppress default HTTP server logging"""
        pass

class GoogleOAuthTokenGenerator:
    """
    Google OAuth 2.0 token generator for API access
    """
    def __init__(self, client_id: str, client_secret: str, api_key: Optional[str] = None):
        """
        Initialize OAuth token generator

        Args:
            client_id: Google OAuth client ID
            client_secret: Google OAuth client secret
            api_key: Google API key (optional, for some operations)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.api_key = api_key
        self.redirect_uri = 'http://localhost:8080'
        self.oauth_server = None

        # Validate inputs
        if not client_id or not client_secret:
            raise ValueError("client_id and client_secret are required")

    def _create_client_config(self) -> Dict[str, Any]:
        """Create client configuration for OAuth flow"""
        return {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.redirect_uri]
            }
        }

    def _generate_pkce_challenge(self) -> Tuple[str, str]:
        """Generate PKCE code verifier and challenge for enhanced security"""
        # Generate code verifier (random string 43-128 characters)
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')

        # Generate code challenge (SHA256 hash of verifier)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')

        return code_verifier, code_challenge

    def _start_callback_server(self) -> int:
        """Start local HTTP server for OAuth callback"""
        for port in range(8080, 8090):  # Try ports 8080-8089
            try:
                self.oauth_server = HTTPServer(('localhost', port), OAuthCallbackHandler)
                self.oauth_server.timeout = 120  # 2 minute timeout

                # Start server in separate thread
                server_thread = threading.Thread(target=self.oauth_server.handle_request)
                server_thread.daemon = True
                server_thread.start()

                return port
            except OSError:
                continue

        raise RuntimeError("Could not start OAuth callback server on any port")

    def get_tokens_interactive(self, scopes: List[str], save_tokens: bool = True,
                               token_file: str = 'google_oauth_tokens.pickle') -> Dict[str, Any]:
        """
        Get OAuth tokens using interactive browser flow

        Args:
            scopes: List of OAuth scopes to request
            save_tokens: Whether to save tokens to file for reuse
            token_file: Path to save/load tokens

        Returns:
            Dictionary containing access_token, refresh_token, and other token info
        """
        try:
            logger.debug("Starting interactive OAuth flow")

            # Check for existing valid tokens
            if save_tokens and os.path.exists(token_file):
                try:
                    with open(token_file, 'rb') as token:
                        creds = pickle.load(token)

                    if creds and creds.valid and set(creds.scopes) >= set(scopes):
                        logger.debug("Using existing valid tokens")
                        return self._credentials_to_dict(creds)
                    elif creds and creds.expired and creds.refresh_token:
                        logger.debug("Refreshing expired tokens")
                        creds.refresh(Request())

                        if save_tokens:
                            with open(token_file, 'wb') as token:
                                pickle.dump(creds, token)

                        return self._credentials_to_dict(creds)
                except Exception as e:
                    logger.warning(f"Could not load existing tokens: {e}")

            # Start OAuth flow
            client_config = self._create_client_config()
            flow = Flow.from_client_config(
                client_config,
                scopes=scopes,
                redirect_uri=self.redirect_uri
            )

            # Start callback server
            port = self._start_callback_server()
            self.redirect_uri = f'http://localhost:{port}'
            flow.redirect_uri = self.redirect_uri

            # Generate authorization URL
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'
            )

            logger.debug(f"Opening browser for authentication: {auth_url}")
            print("Opening browser for Google OAuth authentication...")
            print(f"If browser doesn't open automatically, visit: {auth_url}")

            # Open browser
            webbrowser.open(auth_url)

            # Wait for callback
            logger.debug("Waiting for OAuth callback...")
            self.oauth_server.handle_request()

            # Check for authorization code
            if hasattr(self.oauth_server, 'auth_error') and self.oauth_server.auth_error:
                raise RuntimeError(f"OAuth authorization failed: {self.oauth_server.auth_error}")

            if not hasattr(self.oauth_server, 'auth_code') or not self.oauth_server.auth_code:
                raise RuntimeError("No authorization code received")

            # Exchange code for tokens
            logger.debug("Exchanging authorization code for tokens")
            flow.fetch_token(code=self.oauth_server.auth_code)

            credentials = flow.credentials

            # Save tokens if requested
            if save_tokens:
                with open(token_file, 'wb') as token:
                    pickle.dump(credentials, token)
                logger.debug(f"Tokens saved to {token_file}")

            logger.debug("OAuth flow completed successfully")
            return self._credentials_to_dict(credentials)

        except Exception as e:
            logger.error(f"OAuth flow failed: {e}")
            raise
        finally:
            if self.oauth_server:
                self.oauth_server.server_close()

    def get_tokens_headless(self, scopes: List[str], authorization_code: str) -> Dict[str, Any]:
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
            return self._credentials_to_dict(credentials)

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

            credentials = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret
            )

            credentials.refresh(Request())

            logger.debug("Token refresh completed successfully")
            return self._credentials_to_dict(credentials)

        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            raise

    def validate_tokens(self, access_token: str) -> bool:
        """
        Validate if access token is still valid

        Args:
            access_token: Access token to validate

        Returns:
            True if token is valid, False otherwise
        """
        try:
            # Try to use token with a simple API call
            url = f"https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={access_token}"

            with urllib.request.urlopen(url) as response:
                if response.status == 200:
                    return True
                else:
                    return False

        except Exception:
            return False

    def get_authorization_url(self, scopes: List[str], state: Optional[str] = None) -> str:
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

    def _credentials_to_dict(self, credentials: Credentials) -> Dict[str, Any]:
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

def main():
    """
    Example usage and interactive CLI
    """
    print("Google OAuth Token Generator")
    print("=" * 40)

    # Get credentials from user or environment
    client_id = os.getenv('GOOGLE_CLIENT_ID') or input("Enter Google Client ID: ")
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET') or input("Enter Google Client Secret: ")
    api_key = os.getenv('GOOGLE_API_KEY') or input("Enter Google API Key (optional): ") or None

    if not client_id or not client_secret:
        print("Error: Client ID and Client Secret are required")
        return

    # Initialize generator
    generator = GoogleOAuthTokenGenerator(client_id, client_secret, api_key)

    # Get desired scopes
    scope_input = input("\nEnter scopes (comma-separated names or full URLs): ")
    scope_names = [s.strip() for s in scope_input.split(',')]
    scopes = generator.to_scopes(scope_names)

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
            tokens = generator.get_tokens_interactive(scopes)
            print("\n" + "="*50)
            print("OAUTH TOKENS GENERATED SUCCESSFULLY")
            print("="*50)
            print(f"Access Token: {tokens['access_token']}")
            print(f"Refresh Token: {tokens['refresh_token']}")
            print(f"Expires At: {tokens['expires_at']}")
            print(f"Valid: {tokens['valid']}")

        elif choice == '2':
            # Manual flow
            auth_url = generator.get_authorization_url(scopes)
            print("\nVisit this URL to authorize the application:")
            print(f"{auth_url}")
            print("\nAfter authorization, copy the authorization code and use it with:")
            print("generator.get_tokens_headless(scopes, authorization_code)")

        elif choice == '3':
            # Refresh token
            refresh_token = input("Enter refresh token: ")
            tokens = generator.refresh_tokens(refresh_token)
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
    main()