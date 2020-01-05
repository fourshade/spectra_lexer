""" Main module for the batch and interactive console applications. """

import sys
from time import time

from spectra_lexer.base import Spectra
from spectra_lexer.console import SystemConsole
from spectra_lexer.util.cmdline import CmdlineOption


class SpectraConsole(Spectra):
    """ Run an interactive read-eval-print loop in a new console. """

    def run(self) -> int:
        log = self.build_logger().log
        log("Loading...")
        app = self.build_app()
        self.load_app(app)
        log("Loading complete.")
        namespace = app.console_vars()
        console = SystemConsole.open(namespace)
        console.repl()
        return 0


class SpectraBatchIndex(Spectra):
    """ Analyze translations files and create an examples index from them. Time the execution. """

    # Command-line options necessary to build an index.
    # None does not work as a default value, so represent it with the sentinel value -1.
    index_size: int = CmdlineOption("--size", -1, "Relative size of generated index.")
    process_count: int = CmdlineOption("--processes", 0, "Number of processes used for parallel execution.")

    def run(self) -> int:
        log = self.build_logger().log
        log("Loading...")
        app = self.build_app()
        self.load_app(app)
        log("Loading complete.")
        index_size = None if self.index_size < 0 else self.index_size
        start_time = time()
        log("Operation started...")
        app.make_index(index_size, processes=self.process_count)
        total_time = time() - start_time
        log(f"Operation done in {total_time:.1f} seconds.")
        return 0


console = SpectraConsole.main
index = SpectraBatchIndex.main

if __name__ == '__main__':
    sys.exit(console())
