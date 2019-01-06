"""" Module specifically for configurable components, i.e. those that draw one or more values from a config file. """

from functools import partial, wraps

from spectra_lexer import Component, on

# File name for the standard user config file (in data directory).
_CONFIG_FILE_NAME = "~/config.cfg"


class Configurable(Component):
    """ Configuration manager for the Spectra program. May be configured with command-line arguments.
        Setup must occur before anything configurable is allowed to run. """

    CFG_ROLE = "undefined"  # Heading for config dictionary; overridden by subclasses.
    CFG: dict = {}          # Config dictionary; overridden by subclasses, then by instances at configure time.
    _MASTER: dict = {}      # Configurable master dict; holds all config values for all components.

    @on("start")
    def __start(self, cfg:str=None, **opts) -> None:
        """ Load all config options from disk over the defaults. This is not a simple operation. """
        # Load the config file into the Configurable master dict if it hasn't been loaded yet.
        d = Configurable._MASTER = Configurable._MASTER or self.__load(cfg)
        # Make a save-on-mutate dict out of the default values, then the values from the file on top of them.
        # Give a reference to both the master dict and the instance.
        self.CFG = d[self.CFG_ROLE] = _ConfigDict(self.CFG, **d.get(self.CFG_ROLE, {}))
        self.CFG.save = partial(self.__save, cfg, d)

    def __load(self, path:str) -> dict:
        """ Load the master config dict from either the provided file path (if given) or the user directory. """
        try:
            return self.engine_call("file_load", path or _CONFIG_FILE_NAME)
        except OSError:
            return {}

    def __save(self, path:str, d:dict) -> None:
        """ Save the master config dict to either the provided file path (if given) or the user directory.
            Saving should not fail silently, unlike loading (in which case defaults are used). """
        self.engine_call("file_save", path or _CONFIG_FILE_NAME, d)


def _mutator_hook(func:callable) -> callable:
    @wraps(func)
    def mutate_then_save(self, *args, **kwargs):
        ret = func(self, *args, **kwargs)
        self.save()
        return ret
    return mutate_then_save


# Make a subclass of dict that saves config after any mutating method is called.
_dict_mutators = ["__setitem__", "__delitem__", "clear", "pop", "popitem", "setdefault", "update"]
_saving_mutators = {m: _mutator_hook(getattr(dict, m)) for m in _dict_mutators}
_ConfigDict = type("_ConfigDict", (dict,), _saving_mutators)
