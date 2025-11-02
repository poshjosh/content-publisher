import sys

from enum import Enum, unique
from typing import Any, Optional
from .paths import Paths

@unique
class RunArg(str, Enum):
    def __new__(cls, value: str, alias: str = None, kind: str = 'str',
                optional: bool = False, path: bool = False, default_value: Any = None):
        obj = str.__new__(cls, [value])
        obj._value_ = value
        obj.__alias = alias
        obj.__type = kind
        obj.__optional = optional
        obj.__path = path
        obj.__default_value = default_value
        return obj

    @property
    def alias(self) -> str:
        return self.__alias

    @property
    def type(self) -> str:
        return self.__type

    @property
    def is_optional(self) -> bool:
        return self.__optional

    @property
    def is_path(self) -> bool:
        return self.__path

    @property
    def default_value(self) -> Any:
        return self.__default_value

    DIR = ('dir', 'd', 'str', False, True, "~/.content-publisher/input")
    MEDIA_ORIENTATION = ('orientation', 'o', 'str', False, False, "landscape")
    PLATFORMS = ('platforms', 'p', 'list', False, False, ["youtube","facebook","x","reddit"])
    TEXT_TITLE = ('text-title', 't', 'str')
    TAGS = ('tags', 'tg', 'list', True, False, [])
    LANGUAGE_CODE = ('language-code', 'l', 'str', True, False, 'en')
    VERBOSE = ('verbose', 'v', 'bool', True, False, False)

    @staticmethod
    def of(key: str) -> 'RunArg':
        for run_arg in RunArg:
            if run_arg.value == key or run_arg.alias == key:
                return run_arg
        raise ValueError(f"No RunArg found for key: {key}")

    @staticmethod
    def of_sys_argv(target: dict[str, Any] = None) -> dict['RunArg', Any]:
        return RunArg.of_list(target, sys.argv)

    @staticmethod
    def of_list(target: dict[str, Any] = None, source: Optional[list[str]] = None) -> dict['RunArg', Any]:
        if source is None:
            source = sys.argv

        if target is None:
            target = {}

        # All run args from sys.argv
        for idx, arg in enumerate(source):
            if arg.startswith('--'):
                key = arg[2:]
            elif arg.startswith('-'):
                key = arg[1:]
            else:
                continue

            next_idx = idx + 1

            if len(source) <= next_idx:
                continue

            val = source[next_idx]

            if val is None or val == '':
                continue

            target[RunArg.of(key)] = RunArg.value_of(key, val)

        return target

    @staticmethod
    def value_of(key: str, value: Any) -> Any:
        try:
            for run_arg in RunArg:
                if run_arg.value == key or run_arg.alias == key:
                    return RunArg._parse(run_arg, value)
            return value
        except Exception:
            return value

    @staticmethod
    def _parse(run_arg: 'RunArg', value: str) -> Any:
        if not value:
            return run_arg.default_value
        if run_arg.type == "bool":
            value = value == "true" or value
        elif run_arg.type == "list":
            value = value if isinstance(value, list) else str(value).split(',')
        if run_arg.is_path:
            value = Paths.get_path(value) if run_arg.is_optional else (
                Paths.require_path(value, f"Run option: '{run_arg.value}' is required."))
        return value

