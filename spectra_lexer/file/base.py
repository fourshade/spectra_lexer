""" Module for encoding/decoding dictionaries from various file formats. """

from typing import Iterable

from .resource import Resource


class FileHandler:
    """ Base component class for for file I/O operations to convert between byte strings and dicts. """

    _FORMATS: tuple = ()  # Holds supported file extensions on each subclass.

    def __init_subclass__(cls, formats:Iterable[str]=()):
        """ Supported file extensions include all of those on the base class plus any new ones. """
        cls._FORMATS = (*cls._FORMATS, *formats)

    @classmethod
    def load(cls, filename:str, **kwargs) -> dict:
        """ Attempt to load and decode a single resource (no patterns) given by name. """
        return cls._read(Resource.from_string(filename), **kwargs)

    @classmethod
    def load_all(cls, *patterns:str, **kwargs) -> list:
        """ Attempt to expand all patterns and decode all files in the arguments and return a list. """
        return [cls._read(rs, **kwargs) for p in patterns for rs in Resource.from_pattern(p)]

    @classmethod
    def save(cls, filename:str, d:dict, **kwargs) -> None:
        """ Attempt to encode and save a resource to a file given by name. """
        return Resource.from_string(filename).write(cls.encode(d, **kwargs))

    @classmethod
    def _read(cls, rs:Resource, *, ignore_missing:bool=False, **kwargs) -> dict:
        """ Read and decode a resource into a dict. Missing files may return an empty dict instead of raising. """
        try:
            return cls.decode(rs.read(), **kwargs)
        except OSError:
            if ignore_missing:
                return {}
            raise

    @classmethod
    def decode(cls, contents:bytes, **kwargs) -> dict:
        """ By default, the bytes are not decoded at all, just wrapped in a dict. """
        return {"raw": contents}

    @classmethod
    def encode(cls, d:dict, **kwargs) -> bytes:
        """ We saved the original bytes in the dict under 'raw', so just return that. """
        return d["raw"]

    @classmethod
    def extensions(cls) -> tuple:
        """ Return the extensions of all supported files, including the dot. """
        return cls._FORMATS
