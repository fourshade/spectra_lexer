"""" Module specifically for configurable components, i.e. those that draw one or more values from a config file. """

from typing import Sequence, Type

from spectra_lexer import Component, pipe
from spectra_lexer.resource import ResourceManager
from spectra_lexer.utils import str_eval

# File name for the standard user config file (in app data directory).
_CONFIG_FILE_NAME: str = "~/config.cfg"


class CFGOption:
    """ Descriptor for a configurable setting. Used like an ordinary attribute by the component.
        Requires ConfigManager to update defaults from disk. """

    val: object  # Externally visible value, initialized to default.
    tp: type     # Type of the default value, used for conversion.
    name: str    # Name as shown on config page.
    desc: str    # Description as shown on config page.

    def __init__(self, default:object, name:str, desc:str):
        """ Set the default attributes. """
        self.val = default
        self.tp = type(default)
        self.name = name
        self.desc = desc

    def __get__(self, instance:Component, owner:Type[Component]) -> object:
        """ Config options are accessed through the descriptor by the component itself. """
        return self.val

    def __set__(self, instance:Component, value:object) -> None:
        """ Config values typically come from strings, so they must be converted to the type of the default. """
        self.val = self.tp(value)

    def __set_name__(self, owner:Type[Component], name:str) -> None:
        """ Set an additional attribute on the owner to update this config option. """
        def set_cfg(cmp, cfg_data:dict):
            """ Overwrite this config value with data read from disk (if any).
                Send detailed info about this option to components such as the config editor. """
            v = cfg_data.get(cmp.ROLE, {}).get(name)
            if v is not None:
                setattr(cmp, name, v)
            return cmp.ROLE, name, self
        setattr(owner, "_cfg_" + name, pipe("new_config", "new_config_info", unpack=True)(set_cfg))


class ConfigManager(ResourceManager):
    """ Configuration parser for the Spectra program. Config file may be specified with command-line arguments. """

    ROLE = "config"
    files = [_CONFIG_FILE_NAME]

    _cfg_data: dict  # Dict with config data values loaded from disk.

    def load(self, filenames:Sequence[str]=()) -> dict:
        """ Load and merge all config options from disk. Ignore failures and convert strings using AST. """
        try:
            d = super().load(filenames)
        except OSError:
            d = {}
        self._cfg_data = d
        return d

    def parse(self, d:dict) -> dict:
        """ Try to convert Python literal strings to objects. This fixes crap like bool('False') = True. """
        for (sect, page) in d.items():
            for (opt, val) in page.items():
                if isinstance(val, str):
                    d[sect][opt] = str_eval(val)
        return d

    def inv_parse(self, new_data:dict) -> dict:
        """ Update config options to prepare to save to disk. Saving should not fail silently, unlike loading. """
        for (s, d) in new_data.items():
            self._cfg_data.setdefault(s, {}).update(d)
        return self._cfg_data
