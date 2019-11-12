import sys

from spectra_lexer.base import StenoAppFactory, StenoAppOptions
from spectra_lexer.console import SystemConsole


def main() -> int:
    """ Run an interactive read-eval-print loop in a new console with the app vars as the namespace. """
    options = StenoAppOptions(__doc__)
    options.parse()
    factory = StenoAppFactory(options)
    log = factory.build_logger().log
    log("Loading...")
    app = factory.build_app()
    log("Loading complete.")
    SystemConsole(vars(app)).repl()
    return 0


if __name__ == '__main__':
    sys.exit(main())
