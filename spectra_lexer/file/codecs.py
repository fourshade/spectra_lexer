""" Module for encoding/decoding dictionary data types from files and file-like objects. """

from configparser import ConfigParser
from functools import partial
from io import StringIO
import json
import os

from spectra_lexer.file.resource import Resource

# Allowable prefixes for comments for the CSON decoder. Only full-line comments are currently supported.
_CSON_COMMENT_PREFIXES = ("#", "/")

# JSON standard library functions with default arguments are the fastest way to load structured data in Python.
_decode_JSON = json.loads
# For JSON encoding, indentation allows pretty-printing of results, and Unicode requires an explicit flag to be set.
_encode_JSON = partial(json.dumps, indent=4, ensure_ascii=False)


def _decode_CSON(contents:str) -> dict:
    """ Load a single object from a JSON string with single-line standalone comments. """
    # JSON doesn't care about leading or trailing whitespace, so strip every line.
    stripped_lines = map(str.strip, contents.splitlines())
    # Empty lines and lines starting with a comment tag after stripping are removed before parsing.
    data_lines = [line for line in stripped_lines
                  if line and line[0] not in _CSON_COMMENT_PREFIXES]
    return _decode_JSON("\n".join(data_lines))


def _decode_CFG(contents:str) -> dict:
    """ Decode CFG file contents into a nested dict. A two-level copy must be made to eliminate the proxies. """
    cfg = ConfigParser()
    cfg.read_string(contents)
    return {sect: dict(prox) for (sect, prox) in cfg.items()}


def _encode_CFG(d:dict) -> str:
    """ Encode a dict into a CFG file. Readability may or may not be preserved. """
    cfg = ConfigParser()
    cfg.read_dict(d)
    stream = StringIO()
    cfg.write(stream)
    return stream.getvalue()


# Dictionary containing each supported file format mapped to decoder and encoder functions (and their tuple indices).
CODECS = {".json": (_decode_JSON, _encode_JSON),
          ".cson": (_decode_CSON, _encode_JSON),
          ".cfg":  (_decode_CFG,  _encode_CFG),
          ".ini":  (_decode_CFG,  _encode_CFG)}
_DECODER, _ENCODER = (0, 1)


def _get_codec(f:str) -> tuple:
    """ Return the codec tuple for the given resource, or None if no codec exists.
        It is based only on the extension of the given filename or resource, including the dot. """
    fmt = os.path.splitext(f)[1]
    codec = CODECS.get(fmt)
    if codec is None:
        raise TypeError("No codec found for format {}.".format(fmt))
    return codec


def _check_type(f:str, obj:object, req_type:type=dict) -> None:
    """ Check that the encoded/decoded object matches the expected type. Throw an exception otherwise. """
    if not isinstance(obj, req_type):
        raise TypeError("Unexpected type for file {}: needed {}, got {}".format(f, req_type, type(obj)))


def decode(f:Resource) -> object:
    """ Read and decode a string resource. Throw an exception if the object is not the right type. """
    decoder = _get_codec(f)[_DECODER]
    obj = decoder(f.read())
    _check_type(f, obj)
    return obj


def encode(f:Resource, obj:object) -> None:
    """ Encode a dict into a string resource and write it. Throw an exception if the object is not the right type. """
    encoder = _get_codec(f)[_ENCODER]
    _check_type(f, obj)
    f.write(encoder(obj))
