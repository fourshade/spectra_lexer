""" Main module for the interactive console application. """

import sys

from spectra_lexer import Spectra, SpectraOptions
from spectra_lexer.console import introspect


def main() -> int:
    """ Load basic resources and run an interactive read-eval-print loop in a new console. """
    opts = SpectraOptions("Run Spectra from scratch in an interactive Python console.")
    spectra = Spectra(opts)
    spectra.logger.log("Loading console...")
    return introspect(spectra, include_private=False)


if __name__ == '__main__':
    sys.exit(main())
