""" Module for encoding/decoding dictionaries and other data types from strings. """

from collections import defaultdict
from os.path import splitext
from typing import Callable, Dict, Iterable, List, Type


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


class CodecDatabase:
    """ Global database of supported file formats by subclass. Unlisted formats are decoded as plaintext. """

    _codecs: Dict[str, StringCodec]  # Holds one instance of each codec class.

    def __init__(self, codec_classes:Iterable[Type[StringCodec]]=()):
        """ Create an instance of each subclass codec and register it under each of its file extensions. """
        self._codecs = defaultdict(StringCodec)
        for cls in codec_classes:
            self._codecs.update(dict.fromkeys(cls.FORMATS, cls()))

    def get_decoder(self, f:str) -> Callable[[str], dict]:
        """ Return the decoder function for the given file's extension. """
        return self._codecs[splitext(f)[1]].decode

    def get_encoder(self, f:str) -> Callable[[dict], str]:
        """ Return the encoder function for the given file's extension. """
        return self._codecs[splitext(f)[1]].encode

    def get_formats(self) -> List[str]:
        """ Return the extensions of all supported files, including the dot. """
        return list(self._codecs)
