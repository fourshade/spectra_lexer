from .option import CmdlineParser


class Main:
    """ Abstract base class for a main application entry point. It is meant to contain application options.
        Typically, there will be a number of "Option" objects in the class namespace. These will be
        examined and added to a parser, which will take the command-line arguments and overwrite any
        attributes on the instance that match. Defaults will take over for options with no matches. """

    def __call__(self, script:str="", *argv:str) -> int:
        """ Create an options object, load command line options into it, and call the main entry point function. """
        parser = CmdlineParser(self)
        parser.add_help(script, self.__doc__ or "")
        parser.parse(argv)
        return self.main()

    def main(self) -> int:
        """ Main entry point; returns an int as an exit code. """
        raise NotImplementedError
