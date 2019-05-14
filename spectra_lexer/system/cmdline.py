from argparse import ArgumentParser, SUPPRESS
import sys

from .base import SYS
from spectra_lexer.utils import str_suffix


class CmdlineParser(SYS):
    """ Command line parser for the Spectra program. """

    # Extra keywords for argument parsing based on the option's data type.
    _TYPE_KWDS = {int:  {"type": int},
                  list: {"nargs": "+"}}

    def Load(self) -> None:
        """ Create the parser and add all possible command line options from each component that has some. """
        # Suppress defaults from unused arguments (resources have their own default settings).
        parser = ArgumentParser(argument_default=SUPPRESS)
        # All options handled here must be parsed as long options connected by hyphens.
        for key, default, desc in self.CMDLINE_INFO:
            kwds = {"help": desc, "metavar": str_suffix(key, "-").upper()}
            kwds.update(self._TYPE_KWDS.get(type(default), {}))
            parser.add_argument(f"--{key}", **kwds)
        # Parse arguments from the app using the gathered info.
        # The parser replaces hyphens with underscores, but our keys need the hyphens.
        args_namespace = parser.parse_args(sys.argv[1:])
        # Update all command line options on existing components.
        self.CMDLINE_INFO = [(k.replace("_", "-"), v) for k, v in vars(args_namespace).items()]
