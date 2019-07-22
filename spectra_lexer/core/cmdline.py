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
        args = vars(self.parse_args())
        return {k.replace("_", "-"): args[k] for k in args}


class CmdlineOption:
    """ Class option settable by the command line. """

    _ALL_OPTIONS: dict = {}  # Contains all options declared by imported classes.

    _value: object  # Read-only value for the option.

    def __init__(self, key:str, default=None, desc:str=""):
        self._value = default
        self._ALL_OPTIONS[self] = key, default, desc

    def __get__(self, instance:object, owner:type=None):
        return self._value

    @classmethod
    def process_all(cls) -> None:
        """ Get parameter tuples from every declared option and process them.
            Update all options by setting the value attributes manually. """
        all_opts = cls._ALL_OPTIONS
        parser = CmdlineParser(*all_opts.values())
        parsed_opts = parser.parse()
        for opt, (key, default, desc) in all_opts.items():
            if key in parsed_opts:
                opt._value = parsed_opts[key]
