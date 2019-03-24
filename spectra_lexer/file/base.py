""" Module for encoding/decoding dictionaries and other data types from strings. """

from typing import Iterable

from .resource import Resource


class FileHandler:
    """ Base component class for for file I/O operations to convert between strings and dicts. """

    _FORMATS: list = []  # Holds one instance of each codec class.

    def __init_subclass__(cls, formats:Iterable[str]=()):
        """ Add each new supported file extension to the list. """
        cls._FORMATS = [*cls._FORMATS, *formats]

    @classmethod
    def load(cls, filename:str) -> dict:
        """ Attempt to load and decode a single resource (no patterns) given by name. """
        return cls.decode(Resource.from_string(filename).read())

    @classmethod
    def load_all(cls, *patterns:str) -> list:
        """ Attempt to expand all patterns and decode all files in the arguments and return a list. """
        return [cls.decode(rs.read()) for p in patterns for rs in Resource.from_pattern(p)]

    @classmethod
    def save(cls, filename:str, d:dict) -> None:
        """ Attempt to encode and save a resource to a file given by name. """
        return Resource.from_string(filename).write(cls.encode(d))

    @classmethod
    def decode(cls, contents:str) -> dict:
        raise TypeError("Decoding of this file type is not supported.")

    @classmethod
    def encode(cls, d:dict) -> str:
        raise TypeError("Encoding of this file type is not supported.")

    @classmethod
    def extensions(cls):
        """ Return the extensions of all supported files, including the dot. """
        return cls._FORMATS
