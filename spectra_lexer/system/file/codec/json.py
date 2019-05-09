import json

from .base import Codec, use_if_format_is


@use_if_format_is("json")
class JSON(Codec):
    """ Codec to convert a Python dict to/from a UTF-8 JSON byte string. """

    # JSON standard library functions with default arguments are the fastest way to load structured data in Python.
    decode = staticmethod(json.loads)

    def encode(self, d:dict, **kwargs) -> bytes:
        """ For JSON encoding, an explicit flag is required to preserve Unicode symbols. """
        return json.dumps(d, ensure_ascii=False).encode('utf-8')

    def default(self) -> dict:
        return {}


@use_if_format_is("cson")
class CSON(JSON):
    """ Codec to convert a Python dict to/from a JSON string with full-line comments. """

    def decode(self, contents:bytes, comment_prefixes=frozenset(b"#/"), **kwargs) -> dict:
        """ Load a single object from a JSON string with single-line standalone comments. """
        # JSON doesn't care about leading or trailing whitespace, so strip every line.
        stripped_lines = map(bytes.strip, contents.splitlines())
        # Empty lines and lines starting with a comment tag after stripping are removed before parsing.
        data_lines = [line for line in stripped_lines if line and line[0] not in comment_prefixes]
        return super().decode(b"\n".join(data_lines), **kwargs)
