from types import SimpleNamespace
from typing import Iterable


class Option(SimpleNamespace):
    name: str
    default = None
    title: str = ''
    description: str = ''


class BoolOption(Option):
    default: bool = False


class IntOption(Option):
    default: int = 0


class ConfigSpec(SimpleNamespace):
    options: Iterable[Option]
    name: str = 'DEFAULT'
    title: str = 'General'
