""" Package for common steno system resources. """

from types import SimpleNamespace
from typing import NoReturn


class FrozenStruct(SimpleNamespace):
    """ Immutable attribute-based data structure. """

    def _raise_on_mutate(self, *args) -> NoReturn:
        raise AttributeError('Structure is immutable.')

    __setattr__ = __delattr__ = _raise_on_mutate

    # Identity-based hashing and equality are cheap and usually sufficient.
    # We *could* do value-based hashing on the contents of __dict__ since the structure is frozen,
    # but this is ungodly expensive and makes dictionary lookups over 20 times slower.
    __hash__ = object.__hash__
    __eq__ = object.__eq__
    __ne__ = object.__ne__
