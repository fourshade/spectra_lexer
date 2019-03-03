from argparse import ArgumentParser, SUPPRESS

from spectra_lexer import Component, on, pipe
from spectra_lexer.options import CommandOption


class CmdlineParser(Component):
    """ Command line parser for the Spectra program. """

    ROLE = "cmdline"

    _parser: ArgumentParser  # Holds command line option info from active components.

    def __init__(self):
        # Create the parser and suppress defaults for unused arguments so that they don't override any subclasses.
        super().__init__()
        self._parser = ArgumentParser(description="Steno rule analyzer", argument_default=SUPPRESS)

    @on("new_cmdline_option")
    def add_option(self, key:str, opt:CommandOption):
        """ Add a single command line option with any required keywords. """
        kwds = {"help": opt.desc}
        # If a sequence is the data type, command line arguments must all go in at once.
        if issubclass(opt.tp, (list, tuple)):
            kwds["nargs"] = '+'
        # All named options handled here must be parsed as long options.
        self._parser.add_argument(f"--{key}", **kwds)

    @pipe("cmdline_parse", "new_cmdline_args")
    def parse_args(self, **opts) -> dict:
        """ Send a command to gather all possible command line options and their defaults from all components. """
        self.engine_call("cmdline_get_opts")
        # Parse arguments from sys.argv using the gathered info.
        cmd_opts = vars(self._parser.parse_args())
        # Update all components with the new options. Options from main() have precedence over the command line.
        return {**cmd_opts, **opts}
