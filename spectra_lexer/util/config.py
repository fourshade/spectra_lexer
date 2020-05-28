""" Module for user configuration options stored in the .cfg file format. """

import ast
from configparser import ConfigParser
from typing import Any, Dict

ConfigDict = Dict[str, Any]
NestedConfigDict = Dict[str, ConfigDict]


def eval_str(s:str) -> Any:
    """ Try to evaluate a string as a Python object using ast.literal_eval. This fixes crap like bool('False') = True.
        Strings that are read as names will throw an error, in which case they should be left as-is. """
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

    def read(self, filename:str) -> NestedConfigDict:
        """ Read config settings from a file in .cfg format into a nested mapping. """
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

    def write(self, filename:str, options:NestedConfigDict) -> None:
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


class SimpleConfigDict(ConfigDict):
    """ Configuration dict corresponding to one section of a CFG file. """

    def __init__(self, filename:str, sect="general", *, io:ConfigIO=None) -> None:
        super().__init__()
        self._filename = filename    # Full name of valid file in CFG format.
        self._sect = sect            # Name of our CFG file section.
        self._io = io or ConfigIO()  # Performs whole reads/writes to CFG files.

    def read(self) -> bool:
        """ Try to read config options from the CFG file. Return True if successful. """
        try:
            cfg = self._io.read(self._filename)
            options = cfg.get(self._sect)
            if options:
                self.update(options)
            return True
        except OSError:
            return False

    def write(self) -> bool:
        """ Write the current config options to the original CFG file. Return True if successful. """
        try:
            cfg = {self._sect: self}
            self._io.write(self._filename, cfg)
            return True
        except OSError:
            return False
