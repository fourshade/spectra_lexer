"""" Module specifically for component options, i.e. anything dynamically configured on a global level. """

from argparse import ArgumentParser, SUPPRESS
from typing import Type

from spectra_lexer import Component, pipe


class Option:
    """ Descriptor for a customizable option. Used like an ordinary attribute by the component. """

    val: object = None  # Externally visible value, initialized to default.
    tp: type = None     # Type of the default value, used for conversion.

    def __init__(self, default:object):
        self.val = default
        self.tp = type(default)

    def __get__(self, instance:Component, owner:Type[Component]) -> object:
        """ Options are accessed through the descriptor by the component itself. """
        return self.val

    def __set__(self, instance:Component, value:object) -> None:
        """ Options typically come from strings, so they are converted to the most likely useful type. """
        if self.tp is None or value is None:
            self.val = value
        else:
            self.val = self.tp(value)


class CFGOption(Option):
    """ Descriptor for a file-configurable option. Requires ConfigManager to update defaults from disk. """

    name: str  # Name as shown on config page.
    desc: str  # Description as shown on config page.

    def __init__(self, default:object, name:str, desc:str):
        """ Set the default attributes. """
        super().__init__(default)
        self.name = name
        self.desc = desc

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


class CommandOption(Option):
    """ Descriptor for a command-line option. """

    kwds: dict  # Keywords passed to ArgumentParser.add_argument.

    _OPT_DICT: dict = {}  # Tracks command line options from all component classes.

    def __init__(self, default:object, desc:str):
        """ Set the default value and construct the argparse kwargs. """
        super().__init__(default)
        self.kwds = {"help": desc}

    def __set_name__(self, owner:Type[Component], name:str) -> None:
        """ Set the name, type, and remaining kwargs upon receiving the name and owner class. """
        # Add the object to the global dict under the full name of the long option (without the hyphens).
        self._OPT_DICT[f"{owner.ROLE}_{name}"] = self
        # Use the type annotation as the conversion type if possible, falling back to the default value's type.
        try:
            self.tp = owner.__annotations__[name]
        except (AttributeError, KeyError):
            pass
        # If a sequence is the data type, command line arguments must all go in at once.
        if issubclass(self.tp, (list, tuple)):
            self.kwds["nargs"] = '+'

    @classmethod
    def parse_args(cls, **opts) -> None:
        """ Parse and set all possible command-line arguments from all component classes in global scope. """
        # Suppress defaults for unused arguments so that they don't override the ones from subclasses with None.
        parser = ArgumentParser(description="Steno rule analyzer", argument_default=SUPPRESS)
        args = cls._OPT_DICT
        # Add each argument with its declared keywords as long options.
        for name, obj in args.items():
            parser.add_argument(f"--{name}", **obj.kwds)
        # Command-line options must be prepended to enforce precedence of options from main().
        opts = {**vars(parser.parse_args()), **opts}
        # For any options that were present (either in the command line or in main()), update their values.
        for name, val in opts.items():
            obj = args.get(name)
            if obj is not None:
                obj.val = val
