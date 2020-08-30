import ast
from configparser import ConfigParser
from typing import Any, Dict, Mapping

SectionMapping = Mapping[str, Any]            # Config section mapping option names to values.
ConfigMapping = Mapping[str, SectionMapping]  # Full config mapping by section, then option.
SectionDict = Dict[str, Any]
ConfigDict = Dict[str, SectionDict]


def eval_str(s:str) -> Any:
    """ Try to evaluate a string as a Python literal using ast.literal_eval. This fixes crap like bool('False') = True.
        Strings that are not valid Python literals are returned as-is. """
    try:
        return ast.literal_eval(s)
    except (SyntaxError, ValueError):
        return s


class ConfigIO:
    """ Performs file I/O and data type conversion on the contents of CFG files. """

    def __init__(self, *, from_str=eval_str, to_str=str, encoding='utf-8') -> None:
        self._from_str = from_str  # Converts input strings to other values (default uses ast.literal_eval).
        self._to_str = to_str      # Converts output values back to strings. (default calls __str__).
        self._encoding = encoding  # Character encoding of CFG files.

    def read(self, filename:str) -> ConfigDict:
        """ Read config settings from a file in .cfg format into a nested dictionary. """
        parser = ConfigParser()
        with open(filename, 'r', encoding=self._encoding) as fp:
            parser.read_file(fp)
        options = {}
        for sect in parser:
            page = options[sect] = {}
            for name, s in parser[sect].items():
                value = self._from_str(s)
                page[name] = value
        return options

    def write(self, filename:str, options:ConfigMapping) -> None:
        """ Save a nested mapping of config options to a file in .cfg format by section and name. """
        parser = ConfigParser()
        for sect, page in options.items():
            if page:
                parser.add_section(sect)
                for name, value in page.items():
                    s = self._to_str(value)
                    parser.set(sect, name, s)
        with open(filename, 'w', encoding=self._encoding) as fp:
            parser.write(fp)
