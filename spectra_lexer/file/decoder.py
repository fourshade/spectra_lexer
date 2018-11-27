import json
import os
from typing import Any, Callable, Dict, Iterable, List

# All decoding functions take a file name and return a dict.
# Dictionary containing each supported file extension mapped to its decoding function.
_DECODER_TYPE = Callable[[str], dict]
_DECODERS: Dict[str, _DECODER_TYPE] = {}

# Allowable prefixes for comments for the CSON decoder. Only full-line comments are currently supported.
_CSON_COMMENT_PREFIXES: Iterable[str] = ("#", "//")


def _decodes(*exts:str) -> Callable[[], _DECODER_TYPE]:
    """ Decorator to declare a function's handling of one or more file extensions.
        These extensions will be recorded in the decoder dict as mapping to that function. """
    def ext_recorder(func:_DECODER_TYPE) -> _DECODER_TYPE:
        _DECODERS.update({e: func for e in exts})
        return func
    return ext_recorder


@_decodes(".json")
def _decode_JSON(fname:str) -> Any:
    """ Load a single object from a JSON file. """
    with open(fname, 'rb') as fp:
        contents = fp.read().decode('utf-8')
    return json.loads(contents)


@_decodes(".cson")
def _decode_CSON(fname:str) -> Any:
    """ Load a single object from a JSON file with single-line standalone comments. """
    with open(fname, 'rb') as fp:
        contents = fp.read().decode('utf-8')
    # JSON doesn't care about leading or trailing whitespace, so strip every line.
    stripped_lines = map(str.strip, contents.splitlines())
    # Empty lines and lines starting with a comment tag after stripping are removed before parsing.
    data_lines = [line for line in stripped_lines if line and line[0] not in _CSON_COMMENT_PREFIXES]
    return json.loads("\n".join(data_lines))


def _decode_dict(filename:str) -> dict:
    """ Load the dict found in the given filename (must have a supported file extension). """
    ext = os.path.splitext(filename)[1]
    try:
        d = _DECODERS[ext](filename)
    except KeyError:
        raise KeyError("No decoder found for file extension {}.".format(ext))
    if not isinstance(d, dict):
        raise ValueError("Object decoded from {} is not a dict.".format(filename))
    return d


def recursive_decode_all(filenames:Iterable[str]) -> List[dict]:
    """ Load every rules dict found in the given filenames (and check for str = Iterable[str] bugs).
        Moves deeply through directories and optionally merges all dicts if more than one is found. """
    d_list = []
    if isinstance(filenames, str):
        raise ValueError("Got string argument; need iterable of strings.")
    stack = list(filenames)
    while stack:
        f = stack.pop()
        if os.path.isdir(f):
            stack.extend(os.path.join(f, child) for child in os.listdir(f))
        else:
            try:
                d = _decode_dict(f)
                d_list.append(d)
            except KeyError:
                continue
    return d_list


def get_supported_file_formats() -> List[str]:
    """ Return a list of the supported file format extensions for dict decoding. """
    return sorted(_DECODERS.keys())
