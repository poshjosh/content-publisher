import logging
import requests
from typing import Any, Optional

from ..oauth import OAuth

logger = logging.getLogger(__name__)


# https://developers.facebook.com/docs/facebook-login/guides/access-tokens/#pagetokens
class FacebookOAuth(OAuth):
    def __init__(self, api_endpoint: str, credentials: dict[str, str]):
        super().__init__(credentials)
        self.__client_id = credentials['client_id']
        self.__client_secret = credentials['client_secret']
        self.__redirect_uri = credentials['redirect_uri']
        self.__api_endpoint = api_endpoint
        self.__api_version = api_endpoint.split('/')[-1]

    def _build_auth_url(self, scopes: list[str], _: Optional[dict[str, Any]] = None) -> str:
        return (
            f"https://www.facebook.com/{self.__api_version}/dialog/oauth?"
            f"client_id={self.__client_id}"
            f"&redirect_uri={self.__redirect_uri}"
            f"&scope={','.join(scopes)}"
            f"&response_type=code"
        )

    def _exchange_auth_code_for_access_token(self,
                                             authorization_code: str,
                                             additional_params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        if not authorization_code:
            raise ValueError("Authorization code is required")

        # Exchange authorization code for access token
        token_url = f"{self.__api_endpoint}/oauth/access_token"
        params = {
            'client_id': self.__client_id,
            'client_secret': self.__client_secret,
            'redirect_uri': self.__redirect_uri,
            'code': authorization_code
        }
        
        if additional_params:
            params.update(additional_params)

        response = requests.get(token_url, params=params)
        self._log_response(response)
        response.raise_for_status()

        token_data = response.json()
        
        if token_data and 'access_token' in token_data:
            return self._get_long_lived_user_token(token_data['access_token'])
        
        # TODO - Better to throw exception here
        return token_data

    def _refresh_access_token(self, refresh_token: str) -> Optional[dict[str, Any]]:
        return None

    def _get_long_lived_user_token(self, short_lived_token) -> dict[str, Any]:
        """
        Step 2 (Optional): Exchange short-lived token for long-lived token.
        Long-lived tokens last about 60 days.
        """
        url = f"{self.__api_endpoint}/oauth/access_token"
        params = {
            'grant_type': 'fb_exchange_token',
            'client_id': self.__client_id,
            'client_secret': self.__client_secret,
            'fb_exchange_token': short_lived_token
        }

        response = requests.get(url, params=params)
        self._log_response(response)
        response.raise_for_status()

        return response.json()

    def get_page_access_token(self, page_id: str, user_access_token:str):
        """
        Step 3: Get Page Access Token using User Access Token.
        """
        if not user_access_token:
            raise ValueError("User access token is required")

        url = f"{self.__api_endpoint}/me/accounts"
        params = {'access_token': user_access_token}

        response = requests.get(url, params=params)
        self._log_response(response)
        response.raise_for_status()

        data = response.json()
        pages = data.get('data', [])

        if not pages:
            raise ValueError("No pages found for this user")

        logger.debug(f"\n✓ Found {len(pages)} page(s):")
        for i, page in enumerate(pages, 1):
            logger.debug(f"\t{i}. {page['name']} (ID: {page['id']})")

        for page in pages:
            if page['id'] == page_id:
                return page['access_token'], page
        raise ValueError(f"Page having ID = {page_id} not found")

    def verify_token(self, access_token):
        """
        Verify and inspect an access token.
        Returns token metadata including expiration and permissions.
        """
        url = f"{self.__api_endpoint}/debug_token"
        params = {
            'input_token': access_token,
            'access_token': f"{self.__client_id}|{self.__client_secret}"
        }

        response = requests.get(url, params=params)
        self._log_response(response)
        response.raise_for_status()

        return response.json()['data']

    @staticmethod
    def _log_response(response):
        try:
            logger.debug(f"Response json: {response.json()}")
        except Exception:
            logger.debug(f"Response: {response}")


def main():
    """
    Example usage of the FacebookOAuth class.
    """
    url = "https://graph.facebook.com/v24.0"
    page_id = 'YOUR PAGE ID'
    credentials = {
        'client_id': 'YOUR CLIENT ID',
        'client_secret': 'YOUR CLIENT SECRET',
        'redirect_uri': 'http://localhost:8080/callback'
    }
    # permissions for page posting
    permissions = [
        'pages_show_list',
        'pages_read_engagement',
        'pages_manage_posts',
        'pages_manage_engagement'
    ]

    facebook_oauth = FacebookOAuth(url, credentials)
    print("=" * 60)
    print("Facebook Page Access Token Generator")
    print("=" * 60)

    # Step 1: Get User Access Token
    print("\n[Step 1] Getting User Access Token...")
    user_token = facebook_oauth.get_credentials_interactively(permissions).access_token

    # Step 2: Get Page Access Token
    print("\n[Step 2] Getting Page Access Token...")
    page_token, page_info = facebook_oauth.get_page_access_token(page_id, user_token)

    print("\n" + "=" * 60)
    print("SUCCESS! Tokens obtained:")
    print("=" * 60)
    print(f"\nPage Name: {page_info['name']}")
    print(f"Page ID: {page_info['id']}")
    print(f"\nPage Access Token:\n{page_token}")
    print("\n" + "=" * 60)

    # Verify the token
    print("\nVerifying token...")
    token_info = facebook_oauth.verify_token(page_token)
    print(f"Token Type: {token_info.get('type')}")
    print(f"App ID: {token_info.get('app_id')}")
    print(f"Valid: {token_info.get('is_valid')}")
    print(f"Expires: {token_info.get('expires_at', 'Never (long-lived)')}")


if __name__ == '__main__':
    main()