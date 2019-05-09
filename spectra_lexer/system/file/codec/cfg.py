from configparser import ConfigParser
from io import StringIO

from .base import Codec, use_if_format_is
from spectra_lexer.utils import str_eval


@use_if_format_is("cfg")
@use_if_format_is("ini")
class CFG(Codec):
    """ Codec to convert a nested Python dict to/from a config/INI formatted string. """

    def decode(self, contents:bytes, **kwargs) -> dict:
        """ Decode CFG file contents into a nested dict. A two-level copy must be made to eliminate the proxies. """
        cfg = ConfigParser(**kwargs)
        cfg.read_string(contents.decode('utf-8'))
        d = {}
        for sect, prox in cfg.items():
            if sect != "DEFAULT":
                page = d[sect] = dict(prox)
                for (opt, val) in page.items():
                    # Try to evaluate strings as Python objects. This fixes crap like bool('False') = True.
                    if isinstance(val, str):
                        page[opt] = str_eval(val)
        return d

    def encode(self, d:dict, **kwargs) -> bytes:
        """ Encode a dict into a CFG file. Readability may or may not be preserved. """
        cfg = ConfigParser(**kwargs)
        cfg.read_dict(d)
        stream = StringIO()
        cfg.write(stream)
        return stream.getvalue().encode('utf-8')

    def default(self) -> dict:
        return {}
