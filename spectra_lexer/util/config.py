""" Module for user configuration options stored in the .cfg file format. """

import ast
from configparser import ConfigParser
from typing import Any, Dict, Mapping


class ConfigFile:
    """ Wraps a config file to be read/written by ConfigParser using dicts. """

    def __init__(self, filename:str, *, encoding='utf-8') -> None:
        self._filename = filename  # Full name of valid file in CFG format.
        self._encoding = encoding  # Character encoding of CFG file.

    @staticmethod
    def convert(s:str) -> Any:
        """ Try to evaluate a string as a Python object using AST. This fixes crap like bool('False') = True.
            Strings that are read as names will throw an error, in which case they should be left as-is. """
        try:
            return ast.literal_eval(s)
        except (SyntaxError, ValueError):
            return s

    def read(self) -> Dict[str, Dict[str, Any]]:
        """ Read config settings from a file in .cfg format into a nested dict. """
        parser = ConfigParser()
        with open(self._filename, 'r', encoding=self._encoding) as fp:
            parser.read_file(fp)
        options = {}
        for sect in parser:
            page = options[sect] = {}
            for name, value in parser[sect].items():
                page[name] = self.convert(value)
        return options

    def write(self, options:Mapping[str, Mapping[str, Any]]) -> None:
        """ Save a nested mapping of config options to a file in .cfg format by section and name. """
        parser = ConfigParser()
        for sect, page in options.items():
            if page:
                parser.add_section(sect)
                for name, value in page.items():
                    parser.set(sect, name, str(value))
        with open(self._filename, 'w', encoding=self._encoding) as fp:
            parser.write(fp)
