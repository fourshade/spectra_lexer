from collections import namedtuple
from typing import List

from spectra_lexer.types.codec import CFGDict

# Contains unformatted config info for use in file I/O and parsing.
ConfigParams = namedtuple("ConfigParams", "key default sect name description")
# Contains formatted config info for use in a GUI.
ConfigItem = namedtuple("ConfigItem", "key value title name description")


class ConfigInfo(List[ConfigParams]):
    """ Contains a set of info for config options, such as defaults, a description, etc. """

    def __init__(self, *items:tuple):
        super().__init__([ConfigParams(*params) for params in items])

    def formatted(self, data:dict) -> List[ConfigItem]:
        """ Format the original config params with the current values for display in a configuration window. """
        return [ConfigItem(params.key, data[params.key], params.sect.title(),
                           params.name.replace("_", " ").title(), params.description) for params in self]


class ConfigDictionary:
    """ Dict with config options sorted by state key. """

    _info: ConfigInfo
    _data: dict  # Mapping of config values to internal key.
    _rev: dict   # Mapping of internal keys to section/name required for .CFG format.

    def __init__(self, info:ConfigInfo=()):
        """ Compile a starting config dict from the defined info. """
        self._info = info
        self._data = {}
        self._rev = {}
        for param in info:
            self._data[param.key] = param.default
            self._rev[param.sect, param.name] = param.key

    def info(self) -> List[ConfigItem]:
        return self._info.formatted(self._data)

    def decode_update(self, *data_list:bytes) -> None:
        """ Update the values of each config option from a decoded CFG dict by section and name. """
        for sect, page in CFGDict.decode(*data_list).items():
            for name in page:
                key = self._rev.get((sect, name))
                if key is not None:
                    self._data[key] = page[name]

    def encode_update(self, options:dict) -> bytes:
        """ Encode the values of each option in a CFG dict by section and name. """
        data = self._data
        data.update(options)
        d = CFGDict()
        for (sect, name), key in self._rev.items():
            if key in data:
                if sect not in d:
                    d[sect] = {}
                d[sect][name] = data[key]
        return d.encode()

    def write_to(self, state:dict) -> None:
        """ Add undefined config options to a state dict by key. """
        state.update(self._data, **state)
