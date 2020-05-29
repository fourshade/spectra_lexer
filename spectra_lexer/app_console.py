""" Main module for the interactive console application. """

import sys

from spectra_lexer import SpectraOptions
from spectra_lexer.console.system import SystemConsole


def main() -> int:
    """ Run an interactive read-eval-print loop in a new console. """
    opts = SpectraOptions("Run Spectra from scratch in an interactive Python console.")
    spectra = opts.compile()
    namespace = {"opts": opts, **vars(spectra)}
    console = SystemConsole.open(namespace)
    console.repl()
    return 0


if __name__ == '__main__':
    sys.exit(main())
