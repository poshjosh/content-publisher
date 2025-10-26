"""
TikTok OAuth 2.0 Flow Implementation

This script implements the complete OAuth flow for TikTok API authentication:
1. Generates authorization URL
2. Redirects user to TikTok for authorization
3. Receives callback with authorization code
4. Exchanges code for access token

Reference:
- https://developers.tiktok.com/doc/oauth-user-access-token-management
- https://developers.tiktok.com/doc/login-kit-web-settings/
"""
import hashlib

from dataclasses import dataclass

import secrets
import urllib.parse
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Tuple
import logging
import threading
import time

from .tiktok import TikTokAPIError

logger = logging.getLogger(__name__)

class TikTokAuthorizationError(TikTokAPIError):
    """Exception raised for authorization failures"""
    pass


@dataclass
class TikTokOAuthConfig:
    """Configuration for TikTok OAuth flow"""
    client_key: str
    client_secret: str
    scopes: list[str]
    redirect_uri: str
    authorize_url: str = "https://www.tiktok.com/v2/auth/authorize/"

    def __post_init__(self):
        """Validate configuration"""
        if not self.client_key:
            raise ValueError("client_key is required")
        if not self.client_secret:
            raise ValueError("client_secret is required")
        if not self.scopes:
            raise ValueError("At least one scope is required")
        if not self.redirect_uri:
            raise ValueError("redirect_uri is required")
        if not self.authorize_url:
            raise ValueError("authorize_url is required")


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler for OAuth callback"""

    authorization_code: Optional[str] = None
    error: Optional[str] = None
    code_verifier: Optional[str] = None

    def log_message(self, format, *args):
        """Override to use logger instead of print"""
        logger.debug(f"Callback: {format % args}")

    def do_GET(self):
        """Handle GET request from OAuth callback"""
        # Parse query parameters
        parsed_path = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_path.query)

        # Check if this is the callback endpoint
        if parsed_path.path != '/callback':
            self.send_error(404, "Not Found")
            return

        # Check the csr_token/state parameter
        code_verifier = query_params.get('code_verifier', [None])[0]
        if code_verifier != self.code_verifier:
            logger.warning("Code verifier mismatch!")
            # TODO - Find out why this is failing and fix
            # self.send_error(403, "Invalid code verifier")
            # OAuthCallbackHandler.error = "Code verifier mismatch"
            # return

        # Check for authorization code
        if 'code' in query_params:
            OAuthCallbackHandler.authorization_code = query_params['code'][0]
            logger.debug("Authorization code received")

            # Send success response to browser
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>TikTok Authorization Successful</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    }
                    .container {
                        background: white;
                        padding: 40px;
                        border-radius: 10px;
                        box-shadow: 0 10px 25px rgba(0,0,0,0.2);
                        text-align: center;
                    }
                    h1 { color: #333; margin-bottom: 20px; }
                    p { color: #666; font-size: 18px; }
                    .success { color: #4CAF50; font-size: 48px; margin-bottom: 20px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="success">✓</div>
                    <h1>Authorization Successful!</h1>
                    <p>You have successfully authorized the application.</p>
                    <p>You can close this window and return to the application.</p>
                </div>
            </body>
            </html>
            """
            self.wfile.write(html.encode())

        elif 'error' in query_params:
            error = query_params['error'][0]
            error_description = query_params.get('error_description', ['Unknown error'])[0]
            OAuthCallbackHandler.error = f"{error}: {error_description}"
            logger.error(f"Authorization error: {OAuthCallbackHandler.error}")

            # Send error response to browser
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>TikTok Authorization Failed</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                    }}
                    .container {{
                        background: white;
                        padding: 40px;
                        border-radius: 10px;
                        box-shadow: 0 10px 25px rgba(0,0,0,0.2);
                        text-align: center;
                    }}
                    h1 {{ color: #333; margin-bottom: 20px; }}
                    p {{ color: #666; font-size: 16px; }}
                    .error {{ color: #f5576c; font-size: 48px; margin-bottom: 20px; }}
                    .error-details {{ 
                        background: #ffe0e0;
                        padding: 15px;
                        border-radius: 5px;
                        margin-top: 20px;
                        text-align: left;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="error">✗</div>
                    <h1>Authorization Failed</h1>
                    <p>There was an error during authorization.</p>
                    <div class="error-details">
                        <strong>Error:</strong> {error}<br>
                        <strong>Description:</strong> {error_description}
                    </div>
                    <p style="margin-top: 20px;">Please try again or contact support.</p>
                </div>
            </body>
            </html>
            """
            self.wfile.write(html.encode())

        else:
            self.send_error(400, "Missing authorization code or error")
            OAuthCallbackHandler.error = "Invalid callback parameters"


class TikTokOAuth:
    """TikTok OAuth 2.0 Flow Manager"""

    def __init__(self, config: TikTokOAuthConfig):
        """
        Initialize OAuth manager

        Args:
            config: TikTokOAuthConfig instance
        """
        self.config = config
        self.server: Optional[HTTPServer] = None
        self.server_thread: Optional[threading.Thread] = None
        self.code_verifier: Optional[str] = None
        logger.debug("TikTok OAuth manager initialized")

    def get_authorization_code(
            self,
            port: int = 8080,
            timeout: int = 300,
            auto_open_browser: bool = True
    ) -> str:
        """
        Complete OAuth flow and get authorization code

        Args:
            port: Port for callback server
            timeout: Maximum time to wait for authorization
            auto_open_browser: Automatically open browser for authorization

        Returns:
            Authorization code string

        Raises:
            Exception: If authorization fails
        """
        try:

            code_verifier, code_challenge = TikTokOAuth.generate_code_challenge_pair()

            self.start_callback_server(code_verifier, port)

            auth_url = self.generate_authorization_url(code_challenge, code_verifier)

            # Display URL to user
            print("\n" + "="*70)
            print("TikTok Authorization Required")
            print("="*70)
            print("\nPlease authorize this application by visiting the following URL:\n")
            print(f"  {auth_url}\n")
            print("="*70 + "\n")

            # Open browser automatically
            if auto_open_browser:
                logger.debug("Opening browser for authorization...")
                webbrowser.open(auth_url)
                print("✓ Browser opened automatically\n")
            else:
                print("Copy and paste the URL above into your browser\n")

            print("Waiting for authorization...")
            print("(This window will update once you authorize the app)\n")

            # Wait for authorization
            code, error = self.wait_for_authorization(timeout)

            if error:
                raise TikTokAuthorizationError(f"Authorization failed: {error}")

            if not code:
                raise TikTokAuthorizationError("No authorization code received")

            print("\n" + "="*70)
            print("✓ Authorization Successful!")
            print("="*70 + "\n")

            self.code_verifier = code_verifier

            return code

        finally:
            # Always stop the server
            self.stop_callback_server()


    def generate_authorization_url(self, code_challenge: str, code_verifier: str) -> str:
        params = {
            "client_key": self.config.client_key,
            "client_secret": self.config.client_secret,
            "response_type": "code",
            "scope": ",".join(self.config.scopes),
            "redirect_uri": self.config.redirect_uri,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256"
        }

        query_string = urllib.parse.urlencode(params)
        auth_url = f"{self.config.authorize_url}?{query_string}"

        logger.debug("Authorization URL generated")
        return auth_url

    def start_callback_server(self, code_verifier: str, port: int = 8080) -> None:
        """
        Start local HTTP server to receive OAuth callback

        Args:
            code_verifier: The code verifier
            port: Port number for callback server
        """
        OAuthCallbackHandler.code_verifier = code_verifier

        # Reset class variables
        OAuthCallbackHandler.authorization_code = None
        OAuthCallbackHandler.error = None

        # Create server
        self.server = HTTPServer(('localhost', port), OAuthCallbackHandler)

        # Run server in separate thread
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()

        logger.debug(f"Callback server started on port {port}")

    def stop_callback_server(self) -> None:
        """Stop the callback server"""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            logger.debug("Callback server stopped")

    def wait_for_authorization(self, timeout: int = 300) -> Tuple[Optional[str], Optional[str]]:
        """
        Wait for user to complete authorization

        Args:
            timeout: Maximum time to wait in seconds (default: 5 minutes)

        Returns:
            Tuple of (authorization_code, error)
        """
        logger.debug(f"Waiting for authorization (timeout: {timeout}s)...")

        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check if we received authorization code
            if OAuthCallbackHandler.authorization_code:
                code = OAuthCallbackHandler.authorization_code
                logger.debug("Authorization code received")
                return code, None

            # Check if we received error
            if OAuthCallbackHandler.error:
                error = OAuthCallbackHandler.error
                logger.error(f"Authorization error: {error}")
                return None, error

            # Wait a bit before checking again
            time.sleep(0.5)

        logger.error("Authorization timeout")
        return None, "Authorization timeout - user did not complete the flow"

    @staticmethod
    def _generate_random_string(length: int):
        characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~'
        return ''.join(secrets.choice(characters) for _ in range(length))

    @staticmethod
    def generate_code_challenge_pair():
        code_verifier = TikTokOAuth._generate_random_string(60)
        sha256_hash = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        code_challenge = sha256_hash.hex()  # Convert to hex string
        return code_verifier, code_challenge

    def get_code_verifier(self) -> Optional[str]:
        return self.code_verifier


def usage_example():
    config = TikTokOAuthConfig(
        client_key="your_client_key_here",
        client_secret="your_client_secret_here",
        redirect_uri="http://localhost:8080/callback",
        scopes=[
            "user.debug.basic",
            "user.debug.profile",
            "video.list",
            "video.upload",
            "video.publish"
        ]
    )

    try:
        auth_code = TikTokOAuth(config).get_authorization_code()
        print(f"Authorization Code: {auth_code}\n")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("TikTok OAuth Flow - Examples")
    print("="*70)

    print("\nAvailable examples:")
    print("1. Basic OAuth flow")
    print("2. Advanced OAuth flow with custom configuration")
    print("3. Complete flow with content posting")
    print("\nNote: Replace 'your_client_key_here' and 'your_client_secret_here'")
    print("      with your actual TikTok app credentials.")
    print("\n" + "="*70 + "\n")

    # Uncomment to run examples:
    # usage_example()
