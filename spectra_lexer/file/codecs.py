""" Module for encoding/decoding dictionary data types from files and file-like objects. """

import ast
from collections import defaultdict
from configparser import ConfigParser
from functools import partial
from io import StringIO
import json
import os
from typing import Any

from spectra_lexer.file.resource import Resource

# Allowable prefixes for comments for the CSON decoder. Only full-line comments are currently supported.
_CSON_COMMENT_PREFIXES = ("#", "/")


def _decode_CSON(contents:str) -> dict:
    """ Load a single object from a JSON string with single-line standalone comments. """
    # JSON doesn't care about leading or trailing whitespace, so strip every line.
    stripped_lines = map(str.strip, contents.splitlines())
    # Empty lines and lines starting with a comment tag after stripping are removed before parsing.
    data_lines = [line for line in stripped_lines
                  if line and line[0] not in _CSON_COMMENT_PREFIXES]
    return json.loads("\n".join(data_lines))


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


# Dictionaries containing each supported file format/extension mapped to transcoding functions.
DECODERS = {".json": json.loads, ".cson": _decode_CSON, ".cfg": _decode_CFG, ".ini": _decode_CFG}
# For JSON encoding, indentation allows pretty-printing of results, and Unicode requires an explicit flag to be set.
ENCODERS = {".json": partial(json.dumps, indent=4, ensure_ascii=False), ".cfg": _encode_CFG, ".ini": _encode_CFG}


def decode_resource(f:Resource) -> Any:
    """ Read and decode a string resource. Throw an exception if the object is not the right type. """
    decoder = _get_codec(f, DECODERS)
    obj = decoder(f.read())
    _check_type(f, obj)
    return obj


def encode_resource(f:Resource, obj:Any) -> None:
    """ Encode a dict into a string resource and write it. Throw an exception if the object is not the right type. """
    encoder = _get_codec(f, ENCODERS)
    _check_type(f, obj)
    f.write(encoder(obj))


def _get_codec(f:str, codec_dict:dict) -> callable:
    """ Return the codec function for the given file/resource, or None if no codec exists. """
    fmt = _get_extension(f)
    codec = codec_dict.get(fmt)
    if codec is None:
        raise TypeError("No codec found for format {}.".format(fmt))
    return codec


def _check_type(f:str, obj:object, req_type:type=dict) -> None:
    """ Check that the encoded/decoded object matches the expected type. Throw an exception otherwise. """
    if not isinstance(obj, req_type):
        raise TypeError("Unexpected type for file {}: needed {}, got {}".format(f, req_type, type(obj)))


def _get_extension(name:str) -> str:
    """ Return only the extension of the given filename or resource, including the dot.
        Will return an empty string if there is no extension (such as with a directory). """
    return os.path.splitext(name)[1]
