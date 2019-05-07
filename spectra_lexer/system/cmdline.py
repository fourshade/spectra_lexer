from argparse import ArgumentParser, SUPPRESS

from spectra_lexer.core import Component
from spectra_lexer.utils import str_suffix

# Extra keywords for argument parsing based on the option's data type.
_TYPE_KWDS = {int:  {"type": int},
              list: {"nargs": "+"}}


class CmdlineParser(Component):
    """ Command line parser for the Spectra program. """

    CMDLINE_DESCRIPTION = "Steno rule analyzer"  # Program description as seen in the command line help.

    @init("cmdline")
    def start(self, cmdline:dict) -> None:
        """ Create the parser and add all possible command line options from each component that has some. """
        # Suppress defaults from unused arguments (resources have their own default settings).
        parser = ArgumentParser(description=self.CMDLINE_DESCRIPTION, argument_default=SUPPRESS)
        # All options handled here must be parsed as long options connected by hyphens.
        for key, res in cmdline.items():
            default, desc = res.info()
            kwds = {"help": desc, "metavar": str_suffix(key, "-").upper()}
            kwds.update(_TYPE_KWDS.get(type(default), {}))
            parser.add_argument(f"--{key}", **kwds)
        # Parse arguments from sys.argv using the gathered info.
        # The parser replaces hyphens with underscores, but our keys need the hyphens.
        d = {raw_key.replace("_", "-"): val for raw_key, val in vars(parser.parse_args()).items()}
        self.engine_call("res:cmdline", d, broadcast_depth=1)
