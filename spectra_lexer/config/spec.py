from types import SimpleNamespace
from typing import Any, Dict, Iterable

SectionDict = Dict[str, Any]         # Config section mapping option names to arbitrary values.
ConfigDict = Dict[str, SectionDict]  # Full config dictionary after parsing.


class Option(SimpleNamespace):
    name: str
    default = None
    title: str = ''
    description: str = ''


class BoolOption(Option):
    default: bool = False


class IntOption(Option):
    default: int = 0


class StrOption(Option):
    default: str = ''


class Section(SimpleNamespace):
    options: Iterable[Option]
    name: str = 'DEFAULT'
    title: str = 'General'


ConfigSpec = Iterable[Section]
