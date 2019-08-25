""" Module for console and batch operations. Not very popular... """

from time import time
from typing import Callable, Type, TypeVar

from .app import StenoApplication, StenoOptions
from .cmdline import Option, OptionNamespace
from .console import SystemConsole


class Spectra:
    """ Defines a common lifecycle for each application entry point. """

    NS_TP = TypeVar("NS_TP", bound=OptionNamespace, covariant=True)

    main: Callable[[NS_TP], int]
    opt_cls: Type[NS_TP]

    def __init__(self, main:Callable[[NS_TP], int], opt_cls:Type[NS_TP]) -> None:
        self.main = main
        self.opt_cls = opt_cls

    def __call__(self, *argv:str) -> int:
        """ Load command line options and call the main entry point function. """
        func = self.main
        opts = self.opt_cls("Spectra", func.__doc__)
        opts.parse(argv)
        return func(opts)


def console_main(opts:StenoOptions) -> int:
    """ Run an interactive read-eval-print loop in a new console with the app vars as the namespace. """
    app = StenoApplication(opts)
    SystemConsole(vars(app)).repl()
    return 0


class BatchOptions(StenoOptions):
    """ As part of the built-in resource block, rules have no default save location, so add one. """
    rules_out: str = Option("--rules-out", "./rules.json", "Output file name for lexer-generated rules.")


def timed(func:Callable) -> Callable:
    """ Decorator to make an entry point for a new batch operation. """
    def call(*args) -> int:
        """ Run a batch operation and time its execution. """
        start_time = time()
        print("Operation started...")
        code = func(*args)
        total_time = time() - start_time
        print(f"Operation done in {total_time:.1f} seconds.")
        return code
    return call


@timed
def analyze_main(opts:BatchOptions) -> int:
    """ Run the lexer on every item in a JSON steno translations dictionary. """
    app = StenoApplication(opts)
    app.make_rules(opts.rules_out)
    return 0


@timed
def index_main(*args) -> int:
    """ Analyze translations files and create an index from them. """
    app = StenoApplication(*args)
    app.make_index()
    return 0


console = Spectra(console_main, StenoOptions)
analyze = Spectra(analyze_main, BatchOptions)
index = Spectra(index_main, BatchOptions)
