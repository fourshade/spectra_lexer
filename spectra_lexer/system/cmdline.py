from argparse import ArgumentParser, SUPPRESS

from .app import SYSApp
from spectra_lexer.core import Component, COREApp, Option
from spectra_lexer.utils import str_suffix

# Extra keywords for argument parsing based on the option's data type.
_TYPE_KWDS = {int:  {"type": int},
              list: {"nargs": "+"}}


class CmdlineOption(Option):
    pass


class CmdlineParser(Component,
                    SYSApp.CmdlineArgs,
                    COREApp.Start):
    """ Command line parser for the Spectra program. """

    arg_info: dict = CmdlineOption.init_info()

    def on_app_start(self) -> None:
        """ Create the parser and add all possible command line options from each component that has some. """
        # Suppress defaults from unused arguments (resources have their own default settings).
        parser = ArgumentParser(argument_default=SUPPRESS)
        # All options handled here must be parsed as long options connected by hyphens.
        d = {}
        for key, opt in self.arg_info.items():
            default, desc = opt.info
            d[key] = default
            kwds = {"help": desc, "metavar": str_suffix(key, "-").upper()}
            kwds.update(_TYPE_KWDS.get(type(default), {}))
            parser.add_argument(f"--{key}", **kwds)
        # Parse arguments from the app using the gathered info.
        # The parser replaces hyphens with underscores, but our keys need the hyphens.
        args_namespace = parser.parse_args(self.args)
        d.update({raw_key.replace("_", "-"): val for raw_key, val in vars(args_namespace).items()})
        for k, v in d.items():
            self.engine_call(CmdlineOption.response(k), v)
