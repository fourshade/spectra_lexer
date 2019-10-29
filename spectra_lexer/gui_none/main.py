from time import time

from spectra_lexer.app import StenoApplication
from spectra_lexer.base import StenoMain
from spectra_lexer.console import SystemConsole
from spectra_lexer.option import CmdlineOption


class ConsoleMain(StenoMain):
    """ Run an interactive read-eval-print loop in a new console with the app vars as the namespace. """

    def main(self) -> int:
        logger = self.build_logger()
        logger.log("Loading...")
        app = self.build_app()
        logger.log("Loading complete.")
        SystemConsole(vars(app)).repl()
        return 0


class _BatchMain(StenoMain):
    """ Abstract class; adds batch timing capabilities. """

    processes: int = CmdlineOption("--processes", 0, "Number of processes used for parallel execution.")

    def main(self) -> int:
        """ Run a batch operation and time its execution. """
        start_time = time()
        logger = self.build_logger()
        logger.log("Operation started...")
        app = self.build_app()
        self.run(app)
        total_time = time() - start_time
        logger.log(f"Operation done in {total_time:.1f} seconds.")
        return 0

    def run(self, app:StenoApplication) -> None:
        raise NotImplementedError


class AnalyzeMain(_BatchMain):
    """ Run the lexer on every item in a JSON steno translations dictionary. """

    # As part of the built-in resource block, rules have no default save location, so add one.
    rules_out: str = CmdlineOption("--out", "./rules.json", "JSON output file name for lexer-generated rules.")

    def run(self, app:StenoApplication) -> None:
        app.make_rules(self.rules_out, processes=self.processes)


class IndexMain(_BatchMain):
    """ Analyze translations files and create an index from them. """

    # None does not work as a default value, so represent it with the sentinel value -1.
    index_size: int = CmdlineOption("--size", -1, "Relative size of generated index.")

    def run(self, app:StenoApplication) -> None:
        size = None if self.index_size < 0 else self.index_size
        app.make_index(size, processes=self.processes)
