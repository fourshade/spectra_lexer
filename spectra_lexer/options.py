"""" Module specifically for component options, i.e. anything dynamically configured on a global level. """

from typing import Type

from spectra_lexer import Component, on, pipe


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
        """ Set an additional attribute on the owner class to update this config option on command. """
        def set_cfg(cmp:Component, cfg_data:dict) -> tuple:
            """ Overwrite this config value with data read from disk (if any).
                Send detailed info about this option to components such as the config editor. """
            v = cfg_data.get(cmp.ROLE, {}).get(name)
            if v is not None:
                setattr(cmp, name, v)
            return cmp.ROLE, name, self
        attr = "_cfg_" + name
        set_cfg.__name__ = attr
        setattr(owner, attr, pipe("new_config", "new_config_info")(set_cfg))


class CommandOption:
    """ Descriptor for a command-line argument. Used like an ordinary attribute by the component. """

    val: object  # Externally visible value, initialized to default.
    tp: type     # Type of the default value, used for conversion.
    desc: str    # Description as shown on command line help utility.

    def __init__(self, default:object, desc:str):
        """ Set the default attributes. """
        self.val = default
        self.tp = type(default)
        self.desc = desc

    def __get__(self, instance:Component, owner:Type[Component]) -> object:
        """ Options are accessed through the descriptor by the component itself. """
        return self.val

    def __set__(self, instance:Component, value:object) -> None:
        self.val = value

    def __set_name__(self, owner:Type[Component], name:str) -> None:
        """ Set an additional attribute on the owner class to update this option on start. """
        attr = f"{owner.ROLE}_{name}"
        def set_cmd(cmp:Component, **opts) -> None:
            """ Overwrite this option with data read from the command line (if any). """
            v = opts.get(attr)
            if v is not None:
                setattr(cmp, name, v)
        set_cmd.__name__ = attr
        setattr(owner, attr, on("start")(set_cmd))
