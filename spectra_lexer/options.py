"""" Module specifically for component options, i.e. anything dynamically configured on a global level. """

from typing import Type

from spectra_lexer import Component


class Option:
    """ Descriptor for a customizable option. Used like an ordinary attribute by the component. """

    val: object  # Externally visible value, initialized to default.
    tp: type     # Type of the default value, used for conversion.
    desc: str    # Description as shown on documentation page.

    def __init__(self, default:object, desc:str):
        self.val = default
        self.tp = type(default)
        self.desc = desc

    def __get__(self, instance:Component, owner:Type[Component]) -> object:
        """ Options are accessed through the descriptor by the component itself. """
        return self.val

    def __set__(self, instance:Component, value:object) -> None:
        """ Options typically come from strings, so they are converted to the most likely useful type. """
        if self.tp is None or value is None:
            self.val = value
        else:
            self.val = self.tp(value)

    def __set_name__(self, owner:Type[Component], name:str) -> None:
        """ Use the type annotation as the conversion type if possible, falling back to the default value's type. """
        try:
            self.tp = owner.__annotations__[name]
        except (AttributeError, KeyError):
            pass


class CFGOption(Option):
    """ Descriptor for a file-configurable option. Requires ConfigManager to update defaults from disk. """

    label: str  # Option label as shown on config page.

    def __init__(self, default:object, label:str="", desc:str=""):
        """ Set the default attributes. """
        super().__init__(default, desc)
        self.label = label

    def __set_name__(self, owner:Type[Component], name:str) -> None:
        """ Set an additional attribute on the owner class to update this config option on command. """
        super().__set_name__(owner, name)
        role = owner.ROLE
        def set_cfg(cmp:Component, cfg_data:dict) -> tuple:
            """ Overwrite this config value with data read from disk (if any).
                Send detailed info about this option to components such as the config editor. """
            v = cfg_data.get(role, {}).get(name)
            if v is not None:
                setattr(cmp, name, v)
            return role, name, self
        owner.pipe("new_config", "new_config_info")(set_cfg)


class CommandOption(Option):
    """ Descriptor for a command line option.  Requires CmdlineParser to update defaults. """

    def __set_name__(self, owner:Type[Component], name:str) -> None:
        """ Set additional attributes on the owner class to retrieve and update this option on command. """
        super().__set_name__(owner, name)
        role = owner.ROLE
        def get_arg(cmp:Component) -> tuple:
            """ Send info about this option to the command line parser. """
            return role, name, self
        owner.pipe("cmdline_get_opts", "new_cmdline_option")(get_arg)
        def set_arg(cmp:Component, v:object) -> None:
            """ Overwrite this option with the applicable argument from the command line. """
            setattr(cmp, name, v)
        owner.on(f"cmdline_set_{role}_{name}")(set_arg)
