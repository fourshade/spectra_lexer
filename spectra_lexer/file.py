import json
import os
from typing import Any, Callable, Dict, Iterable, List, NamedTuple

# Local directory containing the built-in JSON rules files
_RULES_DIR: str = os.path.join(os.path.dirname(__file__), "assets")

# All decoding functions take a file name and return a dict.
_DECODER_TYPE = Callable[[str], dict]
# Dictionary containing each supported file extension mapped to its decoding function.
_DECODERS: Dict[str, _DECODER_TYPE] = {}

# Allowable prefixes for comments for the JSON decoder. Only full-line comments are currently supported.
_JSON_COMMENT_PREFIXES: Iterable[str] = ("#", "//")


def _decodes(*exts:str) -> Callable[[], _DECODER_TYPE]:
    """ Decorator to declare a function's handling of one or more file extensions.
        These extensions will be recorded in the decoder dict as mapping to that function. """
    def ext_recorder(func:_DECODER_TYPE) -> _DECODER_TYPE:
        _DECODERS.update({e: func for e in exts})
        return func
    return ext_recorder


@_decodes(".json")
def _decode_JSON(fname: str) -> Any:
    """ Load a single object from a JSON file with single-line standalone comments. """
    with open(fname, 'rb') as fp:
        contents = fp.read().decode('utf-8')
    stripped_lines = filter(None, map(str.strip, contents.splitlines()))
    data_lines = [line for line in stripped_lines if not any(map(line.startswith, _JSON_COMMENT_PREFIXES))]
    try:
        return json.loads("\n".join(data_lines))
    except json.decoder.JSONDecodeError:
        print("Problem decoding JSON file `{}`".format(fname))
        raise


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


def _recursive_decode_all(filenames:Iterable[str]) -> List[dict]:
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


def _merge_dicts(d_iter:Iterable[dict]) -> dict:
    """ Merge all the dicts from an iterable into a new one. """
    merged = {}
    for d in d_iter:
        merged.update(d)
    return merged


def get_file_formats() -> List[str]:
    """ Return a list of the supported file format extensions for file dialogs. """
    return sorted(_DECODERS.keys())


def load_steno_dictionaries(*filenames: str) -> Dict[str, str]:
    """ Load a basic steno dictionary from a supported file.
        For compatibility with Plover, this must remain a basic dict type of stroke:translation string pairs. """
    return _merge_dicts(_recursive_decode_all(filenames))


class RawRulesDictionary(Dict[str, NamedTuple]):
    """
    Class for creating an unformatted rules dictionary from a set of files.
    Each file contains a single JSON dict with the following key-value pairs (all strings):

    key   - A canonical name for the rule. Can be used as a reference in the <pattern> field of other rules.
    value - A list of 2-4 parameters, converted to a named tuple for field access. Each tuple consists of:
    """
    class _RawRule(NamedTuple):
        keys: str              # RTFCRE formatted series of steno strokes.
        pattern: str           # English text pattern, consisting of raw letters as well as references to other rules.
        flag_str: str = ""     # Optional pipe-delimited series of flags.
        description: str = ""  # Optional description for when the rule is displayed in the GUI.

    def __init__(self, *filenames:str):
        """ Load every rules dict found in the given filenames, or the built-in ones if not specified. """
        src_dict = _merge_dicts(_recursive_decode_all(filenames if filenames else [_RULES_DIR]))
        RawRule = self._RawRule
        super().__init__({k: RawRule(*src_dict[k]) for k in src_dict})
