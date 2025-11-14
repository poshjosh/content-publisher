import logging
import threading
import webbrowser

import time
from http.server import HTTPServer
from typing import Optional, Any

logger = logging.getLogger(__name__)

class OAuthError(Exception):
    pass


class OAuthHttpServer(HTTPServer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.oauth_code: Optional[str] = None
        self.oauth_error: Optional[dict[str, Any]] = None
        self.shutdown_initiated: bool = False

class OAuthFlow:
    def __init__(self) -> None:
        self.server: Optional[OAuthHttpServer] = None
        self.server_thread: Optional[threading.Thread] = None

    def start_callback_server(self, callback_handler_class, port: int = 8080, timeout: int = 120):
        """
        Start local HTTP server to receive OAuth callback

        Args:
            callback_handler_class: The request handler class to handle the oauth callback
            port: Port number for callback server
            timeout: Server timeout in seconds
        """
        if self.server:
            raise OAuthError("Callback server is already running")

        self.server = OAuthHttpServer(('localhost', port), callback_handler_class)
        self.server.timeout = timeout

        # Run server in separate thread
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()

        logger.debug(f"Started callback server on port {port}")

    def open_browser(self, auth_url: str):
        print(f"\n{'='*70}\nAuthorization Required\n{'='*70}"
              f"\n\nPlease authorize this application by visiting the following URL:\n"
              f"\n{auth_url}\n{'='*70}\n")
        webbrowser.open(auth_url)
        print("\nWaiting for authorization\n(This window will update once you authorize the app)\n")

    def handle_request(self):
        self.server.handle_request()

    def wait_for_authorization(self, timeout: int = 300) -> str:
        """
        Wait for user to complete authorization

        Args:
            timeout: Maximum time to wait in seconds (default: 5 minutes)

        Returns:
            Tuple of (authorization_code, error)
        """
        logger.debug(f"Waiting for authorization (timeout: {timeout}s)...")
        # self.server.handle_request()

        start_time = time.time()
        while time.time() - start_time < timeout:

            if self.server.oauth_code:
                return self.server.oauth_code

            if self.server.oauth_error:
                raise OAuthError(f"{self.server.oauth_error}")

            # Wait a bit before checking again
            time.sleep(0.5)

        raise OAuthError("Authorization timeout - user did not complete the flow")

    def stop_callback_server(self) -> None:
        if self.server:
            self.server.shutdown_initiated = True
            self.server.shutdown()
            self.server.server_close()
            self.server = None
            logger.debug("Stopped callback server")
