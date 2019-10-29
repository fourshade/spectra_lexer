""" Module for user configuration options. """

import ast
from collections import namedtuple
from typing import Any, Dict, List

# Contains formatted config info for use in a GUI.
ConfigItem = namedtuple("ConfigItem", "key value title name description")


class ConfigOption:
    """ General-purpose configuration option from a CFG file.
        Each one is designed to return a default value until explicitly parsed, at which point
        the descriptor should be overridden by setting the parsed value in the instance dict. """

    def __init__(self, sect:str, name:str, default:Any=None, desc:str="") -> None:
        self.default = default  # The value to be produced if the option is not specified.
        self.sect = sect        # Category/section where option is found.
        self.name = name        # Name of individual option under this category.
        self.desc = desc        # Tooltip string describing the option.

    def __get__(self, instance:object, owner:type=None) -> Any:
        """ Return the default value of the option if accessed directly. """
        return self.default


class ConfigDictionary(dict):
    """ Dict with config options and their corresponding info. """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._info = []  # Contains display info for a set of config options (required for CFG format).

    def add_option(self, key:str, opt:ConfigOption) -> None:
        """ Add an option and start it with the default value. """
        self[key] = opt.default
        self._info.append((key, opt))

    def info(self) -> List[ConfigItem]:
        """ Format the config params with the current values for display in a configuration window. """
        return [ConfigItem(key, self[key], opt.sect.title(), opt.name.replace("_", " ").title(), opt.desc)
                for key, opt in self._info]

    def update_from_cfg(self, options:Dict[str, dict]) -> None:
        """ Update the values of each config option from a CFG-format nested dict by section and name.
            Try to evaluate each string as a Python object using AST. This fixes crap like bool('False') = True.
            Strings that are read as names will throw an error, in which case they should be left as-is. """
        for key, opt in self._info:
            page = options.get(opt.sect, ())
            name = opt.name
            if name in page:
                try:
                    self[key] = ast.literal_eval(page[name])
                except (SyntaxError, ValueError):
                    self[key] = page[name]

    def to_cfg_sections(self) -> Dict[str, dict]:
        """ Save the values of each option into a CFG-format nested dict by section and name and return it. """
        d = {}
        for key, opt in self._info:
            if key in self:
                sect = opt.sect
                if sect not in d:
                    d[sect] = {}
                d[sect][opt.name] = str(self[key])
        return d
