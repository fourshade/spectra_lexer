from argparse import ArgumentParser, SUPPRESS

from spectra_lexer import Component
from spectra_lexer.utils import str_suffix

# Extra keywords for argument parsing based on the option's data type.
_TYPE_KWDS = {int:  {"type": int},
              list: {"nargs": "+"}}


class CmdlineParser(Component):
    """ Command line parser for the Spectra program. """

    _parser: ArgumentParser  # Temporarily holds command line option info from active components.

    @on("set_options")
    def parse_args(self, *, cmdline=(), **options) -> None:
        """ Create the parser and add all possible command line options from each component that has some. """
        # Suppress defaults from unused arguments (components have their own default settings).
        self._parser = ArgumentParser(description="Steno rule analyzer", argument_default=SUPPRESS)
        for opt in cmdline:
            # All options handled here must be parsed as long options connected by hyphens.
            kwds = {"help": opt.desc, "metavar": str_suffix(opt.key, "-").upper()}
            kwds.update(_TYPE_KWDS.get(type(opt.default), {}))
            self._parser.add_argument(f"--{opt.key}", **kwds)
        # Parse arguments from sys.argv using the gathered info.
        d = dict(vars(self._parser.parse_args()))
        # Immediately update all components with the new options. This is required before some of them can run.
        for underscored_key, val in d.items():
            # The parser replaces hyphens with underscores, but our keys need the hyphens.
            key = underscored_key.replace("_", "-")
            self.engine_call(f"set_cmdline_{key}", val)
        # The parser isn't pickleable due to strange internal state, so get rid of it at the end.
        del self._parser
