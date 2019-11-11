from time import time

from spectra_lexer.app import StenoApplication
from spectra_lexer.base import StenoMain
from spectra_lexer.console import SystemConsole
from spectra_lexer.option import CmdlineOption


class ConsoleMain(StenoMain):
    """ Run an interactive read-eval-print loop in a new console with the app vars as the namespace. """

    def main(self) -> int:
        log = self.build_logger().log
        log("Loading...")
        app = self.build_app()
        log("Loading complete.")
        SystemConsole(vars(app)).repl()
        return 0


class IndexMain(StenoMain):
    """ Analyze translations files and create an index from them. Adds batch timing capabilities. """

    # None does not work as a default value, so represent it with the sentinel value -1.
    index_size: int = CmdlineOption("--size", -1, "Relative size of generated index.")
    processes: int = CmdlineOption("--processes", 0, "Number of processes used for parallel execution.")

    def main(self) -> int:
        """ Run a batch operation and time its execution. """
        start_time = time()
        log = self.build_logger().log
        log("Operation started...")
        app = self.build_app()
        self.run(app)
        total_time = time() - start_time
        log(f"Operation done in {total_time:.1f} seconds.")
        return 0

    def run(self, app:StenoApplication) -> None:
        size = None if self.index_size < 0 else self.index_size
        app.make_index(size, processes=self.processes)


console = ConsoleMain()
index = IndexMain()
