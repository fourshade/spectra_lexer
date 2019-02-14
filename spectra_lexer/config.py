"""" Module specifically for configurable components, i.e. those that draw one or more values from a config file. """

from spectra_lexer import Component, pipe


class CFGOption:
    """ Descriptor for a configurable setting. Used like an ordinary attribute by the component. """

    val: object  # Externally visible value, initialized to default.
    tp: type     # Type of the default value, used for conversion.
    name: str    # Name as shown on config page.
    desc: str    # Description as shown on config page.

    def __init__(self, default:object, name:str, desc:str):
        self.val = default
        self.tp = type(default)
        self.name = name
        self.desc = desc

    def __get__(self, instance:Component, owner:type) -> object:
        """ Config options are accessed through the descriptor by the component itself. """
        return self.val

    def __set__(self, instance:Component, value:object) -> None:
        """ Config values typically come from strings, so they must be converted to the type of the default. """
        self.val = self.tp(value)

    def __set_name__(self, owner:type, name:str) -> None:
        """ Add the option to the class config dict under its name. """
        if not hasattr(owner, "cfg_dict"):
            owner.cfg_dict = {}
        owner.cfg_dict[name] = self


class Configurable(Component):
    """ Component that uses user-configurable values. Requires ConfigManager to update these values from defaults. """

    cfg_dict: dict  # Local dict for this component's config option objects.

    @pipe("new_config", "new_config_info", unpack=True)
    def configure(self, cfg_data:dict) -> tuple:
        """ Overwrite (and convert) config values with data read from disk for this role (if any).
            Send detailed info about this component's configuration to components such as the config editor. """
        d = cfg_data.get(self.ROLE, {})
        for k, v in d.items():
            setattr(self, k, v)
        return self.ROLE, self.cfg_dict
