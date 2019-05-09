from typing import Any, List

from spectra_lexer.types import polymorph_index
from spectra_lexer.utils import str_suffix

# Holds supported file formats on each codec subclass.
_FORMAT_INDEX = use_if_format_is = polymorph_index()


class Codec:
    """ Base class for operations to convert between byte strings and other Python objects. """

    def decode(self, contents:bytes, **kwargs) -> Any:
        raise TypeError("Decoding of this format is not supported.")

    def encode(self, obj:Any, **kwargs) -> bytes:
        raise TypeError("Encoding of this format is not supported.")

    def default(self) -> Any:
        return None


def decode(contents:bytes, encoding:str, **kwargs) -> Any:
    """ Decode a series of bytes from <contents> using <encoding>. If contents is None, return a default value. """
    codec = _find(encoding)
    if contents is None:
        return codec.default()
    return codec.decode(contents, **kwargs)


def encode(obj:Any, encoding:str, **kwargs) -> bytes:
    """ Encode a Python object <obj> to bytes using <encoding>. """
    codec = _find(encoding)
    return codec.encode(obj, **kwargs)


def _find(filename_or_encoding:str) -> Codec:
    """ Find and instantiate a suitable codec from a filename or an explicit encoding. """
    encoding = str_suffix(filename_or_encoding, ".")
    try:
        return _FORMAT_INDEX[encoding]()
    except (IndexError, KeyError) as e:
        raise TypeError(f"No valid codec found for encoding {encoding}") from e


def formats() -> List[str]:
    """ Return the formats of all supported files sorted alphabetically. """
    return sorted(_FORMAT_INDEX)
