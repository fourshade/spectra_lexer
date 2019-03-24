from configparser import ConfigParser
from io import StringIO

from .base import FileHandler


class CFG(FileHandler, formats=[".cfg", ".ini"]):
    """ Codec to convert a nested Python dict to/from a config/INI formatted string. """

    @classmethod
    def decode(cls, contents:str) -> dict:
        """ Decode CFG file contents into a nested dict. A two-level copy must be made to eliminate the proxies. """
        cfg = ConfigParser()
        cfg.read_string(contents)
        return {sect: dict(prox) for (sect, prox) in cfg.items()}

    @classmethod
    def encode(cls, d:dict) -> str:
        """ Encode a dict into a CFG file. Readability may or may not be preserved. """
        cfg = ConfigParser()
        cfg.read_dict(d)
        stream = StringIO()
        cfg.write(stream)
        return stream.getvalue()
