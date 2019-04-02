from functools import partial
import json

from .base import FileHandler


class JSON(FileHandler, formats=[".json"]):
    """ Codec to convert a Python dict to/from a standard JSON string. """

    # JSON standard library functions with default arguments are the fastest way to load structured data in Python.
    decode = staticmethod(json.loads)
    # For JSON encoding, an explicit flag is required to preserve Unicode symbols. """
    encode = partial(json.dumps, ensure_ascii=False)


class CSON(JSON, formats=[".cson"]):
    """ Codec to convert a Python dict to/from a JSON string with full-line comments. """

    @classmethod
    def decode(cls, contents:str, comment_prefixes:tuple=("#", "/"), **kwargs) -> dict:
        """ Load a single object from a JSON string with single-line standalone comments. """
        # JSON doesn't care about leading or trailing whitespace, so strip every line.
        stripped_lines = map(str.strip, contents.splitlines())
        # Empty lines and lines starting with a comment tag after stripping are removed before parsing.
        data_lines = [line for line in stripped_lines if line and line[0] not in comment_prefixes]
        return super().decode("\n".join(data_lines), **kwargs)
