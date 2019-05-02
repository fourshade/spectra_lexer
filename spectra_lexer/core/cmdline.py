from argparse import ArgumentParser, SUPPRESS

from spectra_lexer import Component
from spectra_lexer.utils import str_suffix

# Program description as seen in the command line help.
CMDLINE_DESCRIPTION = "Steno rule analyzer"
# Extra keywords for argument parsing based on the option's data type.
_TYPE_KWDS = {int:  {"type": int},
              list: {"nargs": "+"}}


class CmdlineParser(Component):
    """ Command line parser for the Spectra program. """

    _parser: ArgumentParser  # Temporarily holds command line option info from active components.

    @on("init:cmdline", pipe_to="res:cmdline:")
    def start(self, cmdline:dict) -> dict:
        """ Create the parser and add all possible command line options from each component that has some. """
        # Suppress defaults from unused arguments (resources have their own default settings).
        self._parser = ArgumentParser(description=CMDLINE_DESCRIPTION, argument_default=SUPPRESS)
        # All options handled here must be parsed as long options connected by hyphens.
        for key, opt in cmdline.items():
            kwds = {"help": opt.desc, "metavar": str_suffix(key, "-").upper()}
            kwds.update(_TYPE_KWDS.get(type(opt.value), {}))
            self._parser.add_argument(f"--{key}", **kwds)
        # Parse arguments from sys.argv using the gathered info.
        # The parser replaces hyphens with underscores, but our keys need the hyphens.
        d = {raw_key.replace("_", "-"): val for raw_key, val in vars(self._parser.parse_args()).items()}
        # The parser isn't pickleable due to strange internal state, so get rid of it.
        del self._parser
        return d

    @on("init_done", pipe_to="resources_done")
    def done(self) -> tuple:
        """ Assuming all resource-heavy components share this thread, they will be done loading by the time execution
            gets back here, so we should let other threads know that everything is done. """
        return ()

    @on("new_status")
    def display_status(self, msg:str) -> None:
        """ Display engine status and general output messages in the console by default. """
        print(f"SPECTRA: {msg}")
