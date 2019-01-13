"""" Module specifically for configurable components, i.e. those that draw one or more values from a config file. """

from spectra_lexer import Component, pipe


class CFGOption:
    """ Descriptor for a configurable setting. Used like an ordinary attribute by the component. """

    val: object  # Externally visible value, initialized to default.
    tp: type     # Type of the default value, used for conversion.
    name: str    # Name as shown on config page.
    desc: str    # Description as shown on config page.

    def __init__(self, default, name, desc):
        self.val = default
        self.tp = type(default)
        self.name = name
        self.desc = desc

    def __get__(self, instance: Component, owner: type) -> object:
        """ Config options are accessed through the descriptor by the component itself. """
        return self.val


class Configurable(Component):
    """ Component that uses user-configurable values. Requires ConfigManager to update these values from defaults. """

    _cfg_dict: dict  # Local dict for this component's config option objects.

    def __init_subclass__(cls) -> None:
        """ Create the initial config dict from all config options defined in the class body. """
        super().__init_subclass__()
        cls._cfg_dict = {k: v for (k, v) in cls.__dict__.items() if isinstance(v, CFGOption)}

    @pipe("new_config", "new_config_info", unpack=True)
    @classmethod
    def configure(cls, cfg_data:dict):
        """ Overwrite (and convert) config values with data read from disk for this role (if any).
            Send detailed info about this component's configuration to components such as the config editor. """
        new_data = cfg_data.get(cls.ROLE, {})
        for (k, v) in new_data.items():
            option = cls._cfg_dict.get(k)
            if option is not None:
                option.val = option.tp(v)
        return cls.ROLE, cls._cfg_dict
