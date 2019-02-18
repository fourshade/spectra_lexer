import argparse

from spectra_lexer import Process
from spectra_lexer.core import Core


class SpectraApplication(Process):
    """ Process to handle fundamental operations of the Spectra lexer with base components. """

    def __init__(self, *cls_iter:type):
        """ Create all necessary components in order, starting from base components and moving to subclasses. """
        super().__init__(Core, *cls_iter)

    def start(self, **opts) -> None:
        """ Send the start signal with these options, in order of decreasing precedence:
            - Command line arguments parsed from sys.argv.
            - Keyword options given directly by subclasses or by main().
            - Fallback options to load the default config file and rule set.
            Keyword arguments must be combined in a dict in this order to enforce precedence. """
        all_opts = {"config": (), "rules": (), 'translations': None, **opts}
        # Suppress defaults for unused options so that they don't override the ones from subclasses with None.
        parser = argparse.ArgumentParser(argument_default=argparse.SUPPRESS)
        for c in all_opts:
            parser.add_argument('--' + c)
        all_opts.update(vars(parser.parse_args()))
        self.call("start", **all_opts)
