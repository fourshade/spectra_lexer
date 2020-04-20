""" Main module for the batch and interactive console applications. """

import sys
from time import time

from spectra_lexer.base import Spectra
from spectra_lexer.console.system import SystemConsole
from spectra_lexer.util.cmdline import CmdlineOption


def console_main() -> int:
    """ Run an interactive read-eval-print loop in a new console. """
    spectra = Spectra()
    spectra.log("Loading...")
    app = spectra.build_app()
    spectra.load_app(app)
    spectra.log("Loading complete.")
    namespace = app.console_vars()
    console = SystemConsole.open(namespace)
    console.repl()
    return 0


class SpectraIndex(Spectra):
    """ Contains command-line options necessary to build an index. """
    # None does not work as a default value, so represent it with the sentinel value -1.
    index_size: int = CmdlineOption("--size", -1, "Relative size of generated index.")
    process_count: int = CmdlineOption("--processes", 0, "Number of processes used for parallel execution.")


def index_main() -> int:
    """ Analyze translations files and create an examples index from them. Time the execution. """
    spectra = SpectraIndex()
    spectra.log("Loading...")
    app = spectra.build_app()
    spectra.load_app(app)
    spectra.log("Loading complete.")
    index_size = None if spectra.index_size < 0 else spectra.index_size
    start_time = time()
    spectra.log("Operation started...")
    app.make_index(index_size, processes=spectra.process_count)
    total_time = time() - start_time
    spectra.log(f"Operation done in {total_time:.1f} seconds.")
    return 0


if __name__ == '__main__':
    sys.exit(console_main())
