from typing import Union

import os

class Paths:
    @staticmethod
    def get_path(value: any, extra: str = None, default: any = None) -> any:
        if not value:
            return default
        path = Paths.__resolve(value)
        return path if not extra else os.path.join(path, extra)

    @staticmethod
    def require_path(value: any, error_message: Union[str, None] = "A required path was not provided") -> str:
        if not value:
            raise ValueError(error_message)
        path = Paths.__resolve(value)
        if not os.path.exists(path):
            raise FileNotFoundError(f'File not found: {path}')
        return path

    @staticmethod
    def __resolve(path: str) -> str:
        path = os.path.expanduser(os.path.expandvars(path))
        explicit: bool = path.startswith('/') or path.startswith('.')
        return path if explicit else os.path.join(os.getcwd(), path)
