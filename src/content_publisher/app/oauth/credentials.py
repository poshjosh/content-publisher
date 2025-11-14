import copy
import logging
import pickle
import os
from datetime import datetime

from typing import Dict, Any, List, Optional, Callable

from content_publisher.app.oauth.oauth_flow import OAuthError

logger = logging.getLogger(__name__)


class Credentials:
    def __init__(self, data: Dict[str, Any]):
        self.__data = copy.deepcopy(data)
        self.__data['expires_at'] = self._init_expires_at()

    @property
    def data(self) -> Dict[str, Any]:
        return self.__data.copy()

    @property
    def access_token(self) -> Optional[str]:
        return self.__data.get('access_token', None)

    @property
    def refresh_token(self) -> Optional[str]:
        return self.__data.get('refresh_token', None)

    @property
    def scopes(self)  -> List[str]:
        return self.__data.get('scopes', [])

    def with_scopes(self, scopes: List[str]) -> 'Credentials':
        new_data = self.__data.copy()
        new_data['scopes'] = scopes
        return self.__class__(new_data)

    def is_refreshable(self) -> bool:
        return 'refresh_token' in self.__data and self.__data['refresh_token'] is not None

    def is_valid(self, scopes: List[str]) -> bool:
        if 'error' in self.__data.keys():
            return False
        if not self.is_expired():
            return True if not self.scopes else set(self.scopes).issubset(set(scopes))
        return self.is_refreshable()

    def _init_expires_at(self) -> Optional[str]:
        for key in ['expires_in', 'expiry', 'expires_at', 'expires']:
            val = self.__data.get(key)
            if val is None or val == '':
                continue
            try:
                expires_in = float(val) - 30  # 30 seconds buffer
                return datetime.fromtimestamp(datetime.now().timestamp() + expires_in).isoformat()
            except Exception:
                return str(val)
        return None

    def is_expired(self, fallback: bool = False) -> bool:
        if 'expires_at' not in self.__data or self.__data['expires_at'] is None:
            return fallback
        try:
            sval = str(self.__data['expires_at'])
            if '.' in sval:
                expiry = datetime.fromisoformat(sval)
            else:
                expiry = datetime.strptime(sval, '%Y-%m-%dT%H:%M:%S')
            return datetime.now() >= expiry
        except Exception:
            return fallback

    def __str__(self):
        return (f"{self.__class__.__name__}"
                f"(is_expired={self.is_expired()}, expires_at={self.__data.get('expires_at')}, "
                f"access_token={None if self.access_token is None else '***'},"
                f"refresh_token={None if self.refresh_token is None else '***'},"
                f"scopes={self.scopes})")


class CredentialsStore:
    def __init__(self, dir_path: str = '~/.content-publisher/oauth-tokens'):
        self.dir_path = os.path.expanduser(os.path.expandvars(dir_path)) if dir_path else ''
        if self.dir_path and not os.path.exists(self.dir_path):
            os.makedirs(self.dir_path, exist_ok=True)
            logger.debug(f"Created directory {self.dir_path}")

    def load_or_fetch(self,
                      filename: str,
                      fetch: Callable[[Optional[Credentials]], Credentials],
                      scopes: list[str],
                      is_valid: Callable[[Credentials], bool] = lambda credentials: True) -> 'Credentials':
        stored_creds = self.load(filename, scopes)
        if stored_creds and stored_creds.is_expired() is False and is_valid(stored_creds):
            logger.debug(f"Using existing: {stored_creds}")
            return stored_creds
        self.delete(filename)
        fresh_creds = fetch(stored_creds)
        if fresh_creds:
            if 'error' in fresh_creds.data.keys():
                raise OAuthError(fresh_creds.data)
            logger.debug(f"Using newly fetched: {fresh_creds}")
            self.save(filename, fresh_creds.with_scopes(scopes))
        return fresh_creds

    def delete(self, filename: str) -> bool:
        filename = self._file_path(filename)
        if not os.path.exists(filename):
            logger.warning(f"Not found, file: {filename}.")
            return False
        try:
            os.remove(filename)
            logger.debug(f"Deleted: {filename}")
            return True
        except Exception as ex:
            logger.debug(f"Failed to delete: {filename}. Reason: {ex}")
            return False

    def load(self, filename: str, scopes: List[str]) -> Optional[Credentials]:
        filename = self._file_path(filename)
        if not os.path.exists(filename):
            logger.warning(f"Not found, file: {filename}.")
            return None
        try:
            # logger.debug(f"Loading credentials from: {filename}")
            with open(filename, 'rb') as credentials_file:
                creds_data = pickle.load(credentials_file)
                credentials = Credentials(creds_data if creds_data else {})
                logger.debug(f"Loaded {credentials} from: {filename}")

            if credentials.is_valid(scopes):
                return credentials
            else:
                deleted = self.delete(filename)
                if deleted:
                    logger.debug(f"Deleted invalid/expired {credentials} file: {filename}")
                else:
                    logger.debug(f"Failed to delete invalid/expired {credentials} file: {filename}")
                return None
        except Exception as ex:
            logger.warning(f"Could not load credentials from: {filename}. Reason: {ex}")
            return None

    def save(self, filename: str, credentials: Credentials) -> bool:
        filename = self._file_path(filename)
        try:
            dirname = os.path.dirname(filename)
            if not os.path.exists(dirname):
                os.makedirs(dirname, exist_ok=True)
                logger.debug(f"Created directory {dirname}")
            # logger.debug(f"Saving {credentials} to: {filename}")
            with open(filename, 'wb') as credentials_file:
                pickle.dump(credentials.data, credentials_file)
                logger.debug(f"Saved {credentials} to: {filename}")
            return True
        except Exception as ex:
            logger.warning(f"Could not save {credentials} to: {filename}. Reason: {ex}")
            return False

    def _file_path(self, filename: str):
        filename = filename.lstrip('/')
        return os.path.join(self.dir_path, os.path.expanduser(os.path.expandvars(filename)))

