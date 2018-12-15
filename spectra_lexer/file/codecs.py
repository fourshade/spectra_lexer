""" Module for encoding/decoding dictionary data types from files and file-like objects. """

import json
from typing import Callable, Iterable, List

from spectra_lexer.file.io_path import get_file_extension, read_text_asset, read_text_file

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


def _check_and_decode(f_iter:Iterable[str], read_fn:Callable) -> List[dict]:
    """ Check each of the given files/resources and see if they can be decoded,
        For each supported object, decode it into a dict and save it to a list to return.
        Raise a ValueError if there were no objects given or if none of them were decodable. """
    d_list = []
    for f in f_iter:
        fmt = get_file_extension(f)
        decoder = DECODERS.get(fmt)
        if decoder is None:
            continue
        contents = read_fn(f)
        d = decoder(contents)
        if not isinstance(d, dict):
            raise ValueError("Object decoded from {} is not a dict.".format(f))
        d_list.append(d)
    if not d_list:
        raise ValueError("None of the given files/resources were decodable as dictionaries.")
    return d_list


def decode_files(filenames:Iterable[str]) -> List[dict]:
    """ Read and return the contents of each of the given files using standard file I/O operations."""
    return _check_and_decode(filenames, read_fn=read_text_file)


def decode_assets(rnames:Iterable[str]) -> List[dict]:
    """ Read and return the contents of each of the given assets using pkg_resources operations."""
    return _check_and_decode(rnames, read_fn=read_text_asset)
