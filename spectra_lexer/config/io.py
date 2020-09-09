from configparser import ConfigParser
from typing import Dict

SectionStrDict = Dict[str, str]            # Config section mapping option names to string values.
ConfigStrDict = Dict[str, SectionStrDict]  # String config dictionary by section, then option.


class ConfigIO:
    """ Performs string I/O on a single CFG file. """

    def __init__(self, path:str, *, encoding='utf-8') -> None:
        self._path = path          # Full file path to CFG file.
        self._encoding = encoding  # Character encoding of CFG files.

    def read(self) -> ConfigStrDict:
        """ Read config options from a file in .cfg format into a nested string dictionary. """
        parser = ConfigParser()
        with open(self._path, 'r', encoding=self._encoding) as fp:
            parser.read_file(fp)
        return {sect: {**parser[sect]} for sect in parser}

    def write(self, options:ConfigStrDict) -> None:
        """ Save a nested string dictionary of config options to a file in .cfg format. """
        parser = ConfigParser()
        parser.read_dict(options)
        with open(self._path, 'w', encoding=self._encoding) as fp:
            parser.write(fp)
