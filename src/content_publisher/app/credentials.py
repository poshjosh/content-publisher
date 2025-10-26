import logging
import pickle
import os

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)



class Credentials(ABC):
    def __init__(self, data: Dict[str, Any]):
        self.data = data

    @property
    def access_token(self) -> str:
        return self.data.get('access_token', '')

    @property
    def scopes(self)  -> List[str]:
        return self.data.get('scopes', [])

    def is_refreshable(self) -> bool:
        return 'refresh_token' in self.data and self.data['refresh_token'] is not None

    def is_valid(self, scopes: List[str]) -> bool:
        if not self.is_expired():
            return True if not self.scopes else set(self.scopes).issubset(set(scopes))
        return self.is_refreshable()

    @abstractmethod
    def is_expired(self) -> bool:
        raise NotImplementedError()



class CredentialsStore:
    def __init__(self, dir_path: str = '~/.content-publisher/oauth-tokens'):
        self.dir_path = os.path.expanduser(os.path.expandvars(dir_path)) if dir_path else ''
        if self.dir_path:
            os.makedirs(dir_path, exist_ok=True)


    def load(self, filename: str, scopes: List[str]) -> Optional[Credentials]:
        filename = os.path.join(self.dir_path, os.path.expanduser(os.path.expandvars(filename)))
        if not os.path.exists(filename):
            logger.warning(f"Not found, file: {filename}.")
            return None
        try:
            with open(filename, 'rb') as token:
                creds: Credentials = pickle.load(token)

            if creds.is_valid(scopes):
                logger.debug("Using existing valid tokens")
                return creds
            else:
                os.remove(filename)
                logger.debug("Deleted invalid/expired tokens")
                return None
        except Exception as ex:
            logger.warning(f"Could not load existing credentials. Reason: {ex}")
            return None

    def save(self, filename: str, credentials: Credentials):
        filename = os.path.join(self.dir_path, os.path.expanduser(os.path.expandvars(filename)))
        try:
            with open(filename, 'wb') as credentials_file:
                pickle.dump(credentials, credentials_file)
        except Exception as ex:
            logger.warning(f"Could not save credentials. Reason: {ex}")
