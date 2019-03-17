""" Module for encoding/decoding dictionaries and other data types from strings. """

from os.path import splitext
from typing import Callable, Iterable, List


class Codec:
    """ Base class for codecs designed to convert between strings (from files) and dicts (for the program). """

    _TYPES: dict = {}  # Holds one instance of each codec class.

    def __init_subclass__(cls, formats:Iterable[str]=()):
        """ Create an instance of each subclass codec and register it under each of its file extensions. """
        cls._TYPES.update(dict.fromkeys(formats, cls()))

    def decode(self, contents:str) -> dict:
        raise TypeError("Decoding of this file type is not supported.")

    def encode(self, d:dict) -> str:
        raise TypeError("Encoding of this file type is not supported.")

    @classmethod
    def get_formats(cls) -> List[str]:
        """ Return the extensions of all supported files, including the dot. """
        return list(cls._TYPES)

    @classmethod
    def get_decoder(cls, f:str) -> Callable[[str], dict]:
        """ Return the decoder function for the given file's extension. """
        return cls._get_codec(f).decode

    @classmethod
    def get_encoder(cls, f:str) -> Callable[[dict], str]:
        """ Return the encoder function for the given file's extension. """
        return cls._get_codec(f).encode

    @classmethod
    def _get_codec(cls, f:str):
        """ Return the codec for the given file's extension, or if none is found, this one (which raises). """
        return cls._TYPES.get(splitext(f)[1], cls())
