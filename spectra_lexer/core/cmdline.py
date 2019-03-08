from argparse import ArgumentParser, SUPPRESS
from collections import defaultdict

from spectra_lexer import Component
from spectra_lexer.utils import str_suffix

# Extra keywords for argument parsing based on the option's data type.
_TYPE_KWDS = defaultdict(dict, {list: {"nargs": "+"}})


class CmdlineParser(Component):
    """ Command line parser for the Spectra program. """

    ROLE = "cmdline"

    _parser: ArgumentParser = None  # Temporarily holds command line option info from active components.

    @on("cmdline_options")
    def parse_args(self, options:list):
        """ Create the parser and suppress its defaults (components have their own default settings). """
        self._parser = ArgumentParser(description="Steno rule analyzer", argument_default=SUPPRESS)
        # Add all possible command line options to the parser from each component that has some.
        for (key, opt) in options:
            kwds = {"help": opt.desc, "metavar": str_suffix(opt.key, "-").upper(), **_TYPE_KWDS[opt.tp]}
            # All named options handled here must be parsed as long options.
            self._parser.add_argument(f"--{key}", **kwds)
        # Parse arguments from sys.argv using the gathered info.
        d = dict(vars(self._parser.parse_args()))
        # Immediately update all components with the new options. This is required before some of them can run.
        for underscored_key, val in d.items():
            # The parser replaces hyphens with underscores, but our keys need the hyphens.
            key = underscored_key.replace("_", "-")
            self.engine_call(f"set_cmdline_{key}", val)
        # The parser isn't pickleable due to strange internal state, so get rid of it at the end.
        del self._parser
