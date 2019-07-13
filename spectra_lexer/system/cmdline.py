from argparse import ArgumentParser, SUPPRESS


class CmdlineParser(ArgumentParser):
    """ Command line parser for the Spectra program. """

    # Extra keywords for argument parsing based on the option's data type.
    _TYPE_KWDS = {int:  {"type": int},
                  list: {"nargs": "+"}}

    def __init__(self, *options):
        """ Suppress defaults from unused arguments (resources have their own default settings). """
        super().__init__(argument_default=SUPPRESS)
        for opt_args in options:
            self.add_option(*opt_args)

    def add_option(self, key:str, default, desc:str="") -> None:
        """ All options handled here must be parsed as long options connected by hyphens. """
        key_suffix = key.rsplit("-", 1)[-1]
        kwds = {"help": desc, "metavar": key_suffix.upper()}
        tp = type(default)
        if tp in self._TYPE_KWDS:
            kwds.update(self._TYPE_KWDS[tp])
        self.add_argument(f"--{key}", **kwds)

    def parse(self) -> dict:
        """ The parser replaces hyphens with underscores, but our keys need the hyphens. """
        args_dict = vars(self.parse_args())
        return {k.replace("_", "-"): v for k, v in args_dict.items()}
