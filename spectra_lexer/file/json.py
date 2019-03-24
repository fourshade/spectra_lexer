import json

from .base import FileHandler


class JSON(FileHandler, formats=[".json"]):
    """ Codec to convert a Python dict to/from a standard JSON string. """

    # JSON standard library functions with default arguments are the fastest way to load structured data in Python.
    decode = staticmethod(json.loads)

    @classmethod
    def encode(cls, d:dict) -> str:
        """ For JSON encoding, an explicit flag is required to preserve Unicode symbols. """
        return json.dumps(d, ensure_ascii=False, sort_keys=True)


class CSON(JSON, formats=[".cson"]):
    """ Codec to convert a Python dict to/from a JSON string with full-line comments. """

    # Allowable prefixes for comments. Only full-line comments are currently supported.
    _CSON_COMMENT_PREFIXES = ("#", "/")

    @classmethod
    def decode(cls, contents:str) -> dict:
        """ Load a single object from a JSON string with single-line standalone comments. """
        # JSON doesn't care about leading or trailing whitespace, so strip every line.
        stripped_lines = map(str.strip, contents.splitlines())
        # Empty lines and lines starting with a comment tag after stripping are removed before parsing.
        data_lines = [line for line in stripped_lines
                      if line and line[0] not in cls._CSON_COMMENT_PREFIXES]
        return json.loads("\n".join(data_lines))
