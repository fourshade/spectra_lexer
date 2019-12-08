""" Module for user configuration options stored in the .cfg file format. """

import ast
from collections import namedtuple
from configparser import ConfigParser
from typing import Any, List

# Contains formatted config info for use in a GUI.
ConfigItem = namedtuple("ConfigItem", "key value title name description")


class ConfigDictionary:
    """ Contains config options and their corresponding info. """

    def __init__(self) -> None:
        self._data = {}  # Contains all raw config values by a combined section/option string key.
        self._info = []  # Contains display info for a set of config options (required for CFG format).

    def add_option(self, key:str, default:Any=None, desc:str="") -> None:
        """ Add an option under <key> and start it with the <default> value.
            <key> - split by first underscore into:
                sect - Category/section where option is found in a CFG file.
                name - Name of individual option under this category.
            <desc> - Tooltip string describing the option. """
        sect, name = key.split("_", 1)
        self._data[key] = default
        self._info.append((key, sect, name, desc))

    def info(self) -> List[ConfigItem]:
        """ Format the config params with the current values for display in a configuration window. """
        return [ConfigItem(key, self._data[key], sect.title(), name.replace("_", " ").title(), desc)
                for key, sect, name, desc in self._info]

    def update(self, *args, **kwargs) -> None:
        self._data.update(*args, **kwargs)

    def to_dict(self) -> dict:
        return self._data.copy()

    def read_cfg(self, filename:str) -> None:
        """ Read config settings in .cfg format from <filename> and update the values of each config option.
            Try to evaluate each string as a Python object using AST. This fixes crap like bool('False') = True.
            Strings that are read as names will throw an error, in which case they should be left as-is. """
        parser = ConfigParser()
        with open(filename, 'r', encoding='utf-8') as fp:
            parser.read_file(fp)
        for key, sect, name, _ in self._info:
            if sect in parser:
                page = parser[sect]
                if name in page:
                    value = page[name]
                    try:
                        value = ast.literal_eval(value)
                    except (SyntaxError, ValueError):
                        pass
                    self._data[key] = value

    def write_cfg(self, filename:str) -> None:
        """ Save the values of each config option to <filename> in .cfg format by section and name. """
        parser = ConfigParser()
        for key, sect, name, _ in self._info:
            if sect not in parser:
                parser.add_section(sect)
            parser.set(sect, name, str(self._data[key]))
        with open(filename, 'w', encoding='utf-8') as fp:
            parser.write(fp)
