from argparse import ArgumentParser, SUPPRESS

from spectra_lexer import Component
from spectra_lexer.utils import str_suffix

# Extra keywords for argument parsing based on the option's data type.
_TYPE_KWDS = {int:  {"type": int},
              list: {"nargs": "+"}}


class CmdlineParser(Component):
    """ Command line parser for the Spectra program. """

    _parser: ArgumentParser  # Temporarily holds command line option info from active components.

    @on("start")
    def start(self, *, cmdline=(), **options) -> None:
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
        # The parser replaces hyphens with underscores, but our keys need the hyphens.
        d = {underscored_key.replace("_", "-"): val for underscored_key, val in d.items()}
        # Immediately update all components with the new options. This is required before some of them can run.
        for key, val in d.items():
            self.engine_call(f"set_cmdline_{key}", val)
        # The parser isn't pickleable due to strange internal state, so get rid of it.
        del self._parser
        # Let components know the options are done so they can start loading resources.
        self.engine_call("cmdline_opts_done")
        # Assuming all resource-heavy components share this thread, they will be done loading by the time execution
        # gets back here, so we should let other components know that everything is done.
        self.engine_call("cmdline_thread_done")

    @on("new_status")
    def display_status(self, msg:str) -> None:
        """ Display engine status and general output messages in the console by default. """
        print(f"SPECTRA: {msg}")
