""" Main module for the interactive console application. """

import sys

from spectra_lexer import Spectra, SpectraOptions
from spectra_lexer.console.system import SystemConsole


def main() -> int:
    """ Load basic resources and run an interactive read-eval-print loop in a new console. """
    opts = SpectraOptions("Run Spectra from scratch in an interactive Python console.")
    spectra = Spectra(opts)
    spectra.logger.log("Loading...")
    namespace = {k: getattr(spectra, k) for k in dir(spectra) if not k.startswith('_')}
    console = SystemConsole.open(namespace)
    console.repl()
    return 0


if __name__ == '__main__':
    sys.exit(main())
