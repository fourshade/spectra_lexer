from typing import Type

from .option import CmdlineParser


class IMain:
    """ Interface class for a main entry point. """

    def main(self, *args, **kwargs) -> int:
        """ Main entry point; takes varargs and returns an int as an exit code. """
        raise NotImplementedError


class Spectra:
    """ Defines a common startup sequence for each application entry point.
        Each entry point is a function taking a single argument, which can be an object of any type.
        This object is meant to contain application options. It will be constructed with no arguments.
        Typically, these objects contain a number of "Option" objects in the class namespace. These will
        be examined and added to a parser, which will take the command-line arguments and overwrite any
        attributes on the instance that match. Defaults will take over for options with no matches. """

    def __init__(self, main_cls:Type[IMain], *args, **kwargs) -> None:
        self.main_cls = main_cls  # Class with command-line options and a main() method.
        self.args = args          # Positional args given directly to main().
        self.kwargs = kwargs      # Keyword args given directly to main().

    def __call__(self, script:str="", *argv:str) -> int:
        """ Create an options object, load command line options into it, and call the main entry point function. """
        main_obj = self.main_cls()
        parser = CmdlineParser(main_obj)
        parser.add_help(script, main_obj.__doc__)
        parser.parse(argv)
        return main_obj.main(*self.args, **self.kwargs)
