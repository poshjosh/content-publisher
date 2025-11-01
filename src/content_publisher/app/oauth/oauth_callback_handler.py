import logging
import urllib.parse
from http.server import BaseHTTPRequestHandler
from typing import Optional

from ..oauth.oauth_flow import OAuthHttpServer

logger = logging.getLogger(__name__)


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    def get_callback_path(self) -> Optional[str]:
        return None

    def get_params_to_verify(self) -> Optional[dict[str, str]]:
        """Return additional parameters to verify in the callback"""
        return {}  

    def log_message(self, format, *args):
        logger.debug(f"{format % args}")

    def do_GET(self):
        if self.oauth_server.shutdown_initiated:
            html = """
            <!DOCTYPE html>
            <html>
                <head><title>Server Shutting Down</title></head>
                <body><h1>Server is shutting down</h1></body>
            </html> 
            """
            self.send_html(500, html)
            return

        if self.oauth_server.oauth_code:
            html = """
            <!DOCTYPE html>
            <html>
                <head><title>Code Already Received</title></head>
                <body><h1>Code already received</h1></body>
            </html> 
            """
            self.send_html(200, html)
            return

        parsed_path = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_path.query)

        callback_path = self.get_callback_path()
        if callback_path and parsed_path.path != callback_path:
            self.oauth_server.oauth_error = {"code": 404, "message": "Not Found"}
            self.send_error(404, "Not Found")
            return

        params = self.get_params_to_verify()
        if params:
            for param_name, expected_val in params.items():
                param_value = query_params[param_name][0] if param_name in query_params else None
                if expected_val != param_value:
                    self.oauth_server.oauth_error = {"code": 400, "message": f"Invalid/missing parameter: {param_name}"}
                    self.send_error(400, f"Invalid/missing parameter: {param_name}")
                    return

        if 'code' in query_params:
            self.oauth_server.oauth_code = query_params['code'][0]
            logger.debug("Authorization code received")

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
            self.send_html(200, html)

        elif 'error' in query_params:
            code = 400
            error_param = query_params['error'][0]
            error_description = query_params.get('error_description', ['Unknown error'])[0]
            self.oauth_server.oauth_error = {"code": code, "error": error_param, "message": error_description}
            logger.error(f"Authorization error: {self.oauth_server.oauth_error}")

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
                        <strong>Code:</strong> 400<br>
                        <strong>Error:</strong> {error_param}<br>
                        <strong>Description:</strong> {error_description}
                    </div>
                    <p style="margin-top: 20px;">Please try again or contact support.</p>
                </div>
            </body>
            </html>
            """
            self.send_html(code, html)
        else:
            self.oauth_server.oauth_error = {"code": 400, "message": "Invalid callback parameters"}
            self.send_error(400, "Missing authorization code or error")

    def send_html(self, code: int, html: str):
        self.send_response(code)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())

    @property
    def oauth_server(self) -> OAuthHttpServer:
        if isinstance(self.server, OAuthHttpServer):
            return self.server
        else:
            raise RuntimeError(f"Expected an instance of OAuthHttpServer, but got: {type(self.server)}")
