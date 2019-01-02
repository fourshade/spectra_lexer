""" Module for encoding/decoding dictionary data types from files and file-like objects. """

import json
from typing import Iterable

from spectra_lexer.file.io_path import get_extension, Readable, Writeable

# Allowable prefixes for comments for the CSON decoder. Only full-line comments are currently supported.
_CSON_COMMENT_PREFIXES: Iterable[str] = ("#", "/")


def _decode_CSON(contents:str) -> dict:
    """ Load a single object from a JSON string with single-line standalone comments. """
    # JSON doesn't care about leading or trailing whitespace, so strip every line.
    stripped_lines = map(str.strip, contents.splitlines())
    # Empty lines and lines starting with a comment tag after stripping are removed before parsing.
    data_lines = [line for line in stripped_lines
                  if line and line[0] not in _CSON_COMMENT_PREFIXES]
    return json.loads("\n".join(data_lines))


# Dictionaries containing each supported file format/extension mapped to transcoding functions.
# Converting between dicts and pure JSON strings is easy, but stripping comments requires an extra step.
ENCODERS = {".json": json.dumps}
DECODERS = {".json": json.loads, ".cson": _decode_CSON}


def decode_resource(f:Readable) -> dict:
    """ Read and decode a string resource into a dict. """
    decoder = _get_codec(f, DECODERS)
    if decoder is None:
        raise ValueError("No decoder found for {}.".format(f))
    d = decoder(f.read())
    if not isinstance(d, dict):
        raise ValueError("Object decoded from {} is not a dict.".format(f))
    return d


def encode_resource(f:Writeable, d:dict) -> None:
    """ Encode a dict into a string resource and write it. """
    if not isinstance(d, dict):
        raise ValueError("Object to be encoded to {} is not a dict.".format(f))
    encoder = _get_codec(f, ENCODERS)
    if encoder is None:
        raise ValueError("No encoder found for {}.".format(f))
    f.write(encoder(d))


def _get_codec(f:str, codec_dict:dict) -> callable:
    """ Return the codec function for the given file/resource, or None if no codec exists. """
    fmt = get_extension(f)
    return codec_dict.get(fmt)
