""" Module for encoding/decoding dictionaries and other data types from strings. """

from typing import Iterable

from .resource import Resource


class FileHandler:
    """ Base component class for for file I/O operations to convert between strings and dicts. """

    _FORMATS: list = []  # Holds each supported file extension.

    def __init_subclass__(cls, formats:Iterable[str]=()):
        """ Add each new supported file extension to the list. """
        cls._FORMATS = [*cls._FORMATS, *formats]

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
    def decode(cls, contents:str, **kwargs) -> dict:
        raise TypeError("Decoding of this file type is not supported.")

    @classmethod
    def encode(cls, d:dict, **kwargs) -> str:
        raise TypeError("Encoding of this file type is not supported.")

    @classmethod
    def extensions(cls):
        """ Return the extensions of all supported files, including the dot. """
        return cls._FORMATS
