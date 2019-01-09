"""" Module specifically for configurable components, i.e. those that draw one or more values from a config file. """

from spectra_lexer import Component, on


class Configurable(Component):
    """ Component that uses user-configurable values. Requires ConfigManager to update these values from defaults. """

    CFG_ROLE = "undefined"  # Heading for config dictionary; overridden by subclasses.
    CFG: dict = {}          # Local config dictionary, loaded with default values by subclasses.

    @on("configure")
    def configure(self, cfg_dict:dict) -> None:
        """ Override default values from the class CFG dict with those read from disk for this role (if any).
            Store the class dict back in the config structure so it gets saved with everything else. """
        self.CFG.update(cfg_dict.get(self.CFG_ROLE, {}))
        cfg_dict[self.CFG_ROLE] = self.CFG

    def __getitem__(self, opt:str):
        """ Config options can be accessed through the component itself as a container. """
        return self.CFG[opt]

    def __setitem__(self, opt:str, val) -> None:
        """ Config options set through the container protocol are immediately saved. """
        self.CFG[opt] = val
        self.engine_call("config_save")
