import ast
from collections import namedtuple
from typing import Dict, List

# Contains formatted config info for use in a GUI.
ConfigItem = namedtuple("ConfigItem", "key value title name description")


class ConfigDictionary(dict):
    """ Dict with config options sorted by state key. """

    _info: List[tuple]      # Contains a set of info for config options, such as defaults, a description, etc.
    _rev: Dict[tuple, str]  # Mapping of internal keys to section/name required for .CFG format.

    def __init__(self, info:List[tuple]) -> None:
        """ Compile a starting config dict from the defined info. """
        super().__init__()
        self._info = [*info]
        self._rev = {}
        for key, default, sect, name, description in info:
            self[key] = default
            self._rev[sect, name] = key

    def info(self) -> List[ConfigItem]:
        """ Format the config params with the current values for display in a configuration window. """
        return [ConfigItem(key, self[key], sect.title(), name.replace("_", " ").title(), description)
                for key, default, sect, name, description in self._info]

    def sectioned_update(self, options:Dict[str, dict]) -> None:
        """ Update the values of each config option from a nested dict by section and name.
            Try to evaluate each string as a Python object using AST. This fixes crap like bool('False') = True.
            Strings that are read as names will throw an error, in which case they should be left as-is. """
        for sect, page in options.items():
            for name, value in page.items():
                key = self._rev.get((sect, name))
                if key is not None:
                    try:
                        value = ast.literal_eval(value)
                    except (SyntaxError, ValueError):
                        pass
                    self[key] = value

    def sectioned_data(self) -> Dict[str, dict]:
        """ Save the values of each option into a nested dict by section and name and return it. """
        d = {}
        for (sect, name), key in self._rev.items():
            if key in self:
                if sect not in d:
                    d[sect] = {}
                d[sect][name] = str(self[key])
        return d
