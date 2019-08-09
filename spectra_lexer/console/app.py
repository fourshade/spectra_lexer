from time import time

from spectra_lexer import StenoApplication
from spectra_lexer.cmdline import CmdlineOption


def console(*argv) -> int:
    """ Run interactive console operations. """
    app = StenoApplication(*argv)
    app.repl()
    return 0


def batch_runner(app_cls:type):
    """ Decorator to make an entry point from a batch operation class. """
    def run(*argv:str) -> int:
        """ Run a batch operation with a new instance of a runnable app class and time its execution. """
        app = app_cls(*argv)
        start_time = time()
        print("Operation started...")
        result = app.run()
        total_time = time() - start_time
        print(f"Operation done in {total_time:.1f} seconds.")
        return result
    return run


@batch_runner
class analyze(StenoApplication):

    rules_out: str = CmdlineOption("rules-out", default="./rules.json",
                                   desc="Output file name for lexer-generated rules.")

    def run(self) -> int:
        """ Run the lexer on every item in a JSON steno translations dictionary. """
        rules = self.steno.LXAnalyzerMakeRules()
        self.steno.RSRulesSave(rules, self.rules_out)
        return 0


@batch_runner
class index(StenoApplication):

    def run(self) -> int:
        """ Analyze translations files and creates indices from them. """
        index = self.steno.LXAnalyzerMakeIndex()
        self.steno.RSIndexSave(index)
        return 0
