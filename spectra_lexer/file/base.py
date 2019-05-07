""" Module for encoding/decoding Python objects from various file formats. """

from typing import Any

from .path import Path, PathFinder
from spectra_lexer.types import polymorph_index

# Holds supported file extensions on each subclass.
use_if_format_is = polymorph_index()
_FORMAT_INDEX = use_if_format_is.items()


class FileHandler:
    """ Base component class for for file I/O operations to convert between byte strings and dicts. """

    @classmethod
    def load(cls, filename:str, **kwargs) -> Any:
        """ Attempt to load and decode a single resource (no patterns) given by name. """
        return cls._read(PathFinder.from_string(filename), **kwargs)

    @classmethod
    def load_all(cls, *patterns:str, **kwargs) -> list:
        """ Attempt to expand all patterns and decode all files in the arguments and return a list. """
        return [cls._read(rs, **kwargs) for p in patterns for rs in PathFinder.list_from_pattern(p)]

    @classmethod
    def save(cls, filename:str, d:dict, **kwargs) -> None:
        """ Attempt to encode and save a resource to a file given by name. """
        return PathFinder.from_string(filename).write(cls.encode(d, **kwargs))

    @classmethod
    def _read(cls, rs:Path, *, ignore_missing:bool=False, **kwargs) -> Any:
        """ Read and decode a file resource. Missing files may return a default object instead of raising. """
        try:
            return cls.decode(rs.read(), **kwargs)
        except OSError:
            if ignore_missing:
                return cls.on_missing()
            raise

    @classmethod
    def decode(cls, contents:bytes, **kwargs) -> Any:
        raise TypeError("Decoding of this format is not supported.")

    @classmethod
    def encode(cls, d:dict, **kwargs) -> bytes:
        raise TypeError("Encoding of this format is not supported.")

    @classmethod
    def on_missing(cls) -> Any:
        """ The return value for a missing file should evaluate as boolean False at minimum. """
        return None

    @classmethod
    def extensions(cls) -> list:
        """ Return the extensions of all supported files, including the dot. """
        return sorted(ext for ext, tp in _FORMAT_INDEX if issubclass(cls, tp))
