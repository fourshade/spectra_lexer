""" Package for common steno system resources. """

from types import SimpleNamespace
from typing import NoReturn


class FrozenStruct(SimpleNamespace):
    """ Immutable attribute-based data structure. """

    def __setattr__(self, *args) -> NoReturn:
        raise AttributeError('Structure is immutable.')
