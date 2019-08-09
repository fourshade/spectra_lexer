from argparse import ArgumentParser, SUPPRESS
from collections import namedtuple
from typing import List, Tuple


class CmdlineOption(namedtuple("CmdlineOption", "key default desc")):
    """ Class option settable by the command-line parser. """

    def __get__(self, instance:object, owner:type=None):
        """ If not otherwise overridden, return the option's default value on instance attribute access. """
        return self.default


class CmdlineParser:
    """ Command line parser for the Spectra program. """

    # Extra keywords for argument parsing based on the option's data type.
    _TYPE_KWDS = {int:  {"type": int},
                  list: {"nargs": "+"}}

    _parser: ArgumentParser
    _host_attrs: List[Tuple[object, str, str]]

    def __init__(self):
        """ Suppress defaults from unused arguments (options have their own default settings). """
        self._parser = ArgumentParser(argument_default=SUPPRESS)
        self._host_attrs = []

    def add_host(self, host:object) -> None:
        """ Add all command line options registered on the given host's class hierarchy to the parser and list. """
        for cls in type(host).__mro__:
            for attr, obj in vars(cls).items():
                if isinstance(obj, CmdlineOption):
                    self._add_option(obj)
                    self._host_attrs.append((host, attr, obj.key))

    def _add_option(self, opt:CmdlineOption) -> None:
        """ All options handled here must be parsed as long options connected by hyphens. """
        key_suffix = opt.key.rsplit("-", 1)[-1]
        kwds = {"help": opt.desc, "metavar": key_suffix.upper()}
        tp = type(opt.default)
        if tp in self._TYPE_KWDS:
            kwds.update(self._TYPE_KWDS[tp])
        self._parser.add_argument(f"--{opt.key}", **kwds)

    def parse(self, *argv:str) -> None:
        """ Parse the given arguments and update all options by setting attributes on the hosts. """
        d = vars(self._parser.parse_args(argv))
        # The parser replaces hyphens with underscores, but our keys need the hyphens.
        parsed_opts = {k.replace("_", "-"): d[k] for k in d}
        for host, attr, key in self._host_attrs:
            if key in parsed_opts:
                setattr(host, attr, parsed_opts[key])
