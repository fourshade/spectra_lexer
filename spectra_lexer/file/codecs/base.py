""" Module for encoding/decoding dictionaries and other data types from strings. """

import os
from typing import Callable, DefaultDict, Iterable, List, Type


class StringCodec:
    """ Base class for codecs designed to convert between strings (from files) and dicts (for the program)
        Default behavior processes files as plaintext, wrapping their contents as a single item in a dict. """

    FORMATS: Iterable[str] = ()  # List of supported file formats local to each subclass.

    def decode(self, contents:str) -> dict:
        """ Just return the bare string wrapped in a dict. """
        return {"raw": contents}

    def encode(self, d:dict) -> str:
        """ Unwrap the string and return it. """
        return d["raw"]


class CodecDict(DefaultDict[str, StringCodec]):
    """ Global dict of supported file formats by subclass. Any unlisted formats are decoded as plaintext. """

    def __init__(self, codecs:Iterable[Type[StringCodec]]):
        """ Create an instance of each subclass codec and register it under each of its file extensions. """
        super().__init__(StringCodec)
        for cls in codecs:
            self.update(dict.fromkeys(cls.FORMATS, cls()))

    def get_decoder(self, f:str) -> Callable[[str], dict]:
        """ Return the decoder function for the given file's extension. """
        return self[_get_ext(f)].decode

    def get_encoder(self, f:str) -> Callable[[dict], str]:
        """ Return the encoder function for the given file's extension. """
        return self[_get_ext(f)].encode

    def get_formats(self) -> List[StringCodec]:
        """ Return the extensions of all supported files, including the dot. """
        return list(self)


def _get_ext(f:str) -> str:
    """ Return the extension of the given filename or resource, including the dot. """
    return os.path.splitext(f)[1]
