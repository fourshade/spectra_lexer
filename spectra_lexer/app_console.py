""" Main module for the interactive console application. """

import sys

from spectra_lexer import Spectra
from spectra_lexer.console.system import SystemConsole
from spectra_lexer.util.cmdline import CmdlineOptions


def main() -> int:
    """ Run an interactive read-eval-print loop in a new console. """
    opts = CmdlineOptions("Run Spectra from scratch in an interactive Python console.")
    spectra = Spectra(opts)
    namespace = {k: getattr(spectra, k) for k in dir(spectra) if not k.startswith("_")}
    console = SystemConsole.open(namespace)
    console.repl()
    return 0


if __name__ == '__main__':
    sys.exit(main())
