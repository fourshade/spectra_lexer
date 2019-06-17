""" Master console script and primary entry point for the Spectra program. """

import sys

# Be sure to import every package with at least one entry point.
from spectra_lexer import core, gui_http, gui_qt, plover, steno


def main() -> int:
    """ The first command-line argument determines the entry point/mode to run.
        Remove it, but keep any subsequent arguments. """
    mode = sys.argv[1:2]
    del sys.argv[1:2]
    return core.main(*mode)


if __name__ == '__main__':
    sys.exit(main())
