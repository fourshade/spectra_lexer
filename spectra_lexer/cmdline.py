""" Module for user-configurable command-line options. """

import os
import sys
from typing import Any, Iterable, List, Sequence


class _CmdlineArgument:
    """ Abstract class for information about a single argument from the command line. """

    keys: Sequence[str]  # Contains all unique command-line option strings that cause this action.
    desc: str            # The help string describing the argument.

    def __call__(self, *args:str) -> Any:
        """ An option will return a value based on zero or more argument strings. """
        raise NotImplementedError

    def __str__(self) -> str:
        """ Return a usage string for this option based on its keys. """
        return "|".join(self.keys)


class CmdlineOption(_CmdlineArgument):
    """ A command-line option corresponding to a single object which can be placed in an attribute.
        Each one is designed to return a default value until explicitly parsed, at which point
        the descriptor should be overridden by setting the parsed value in the instance dict. """

    def __init__(self, key:str, default:Any=None, desc:str="No description.") -> None:
        self.keys = [key]
        self.default = default  # The value to be produced if the option is not specified.
        self.desc = desc

    def __get__(self, instance:object, owner:type=None) -> Any:
        """ Return the default value of the option if accessed directly. """
        return self.default

    def __call__(self, *args:str) -> Any:
        """ Usually a single value is returned. multiargs=True will produce a list, even with only one value. """
        value = [*map(self._ctor(), args)]
        if not self._multiargs():
            if len(value) != 1:
                raise ValueError(f'Option {self.keys} takes exactly one argument, got {len(value)}.')
            value = value[0]
        return value

    def __str__(self) -> str:
        argstr = "|".join(self.keys)
        metavar = f'<{self._ctor().__name__}>'
        argstr += f'={metavar}'
        if self._multiargs():
            argstr += f' [{metavar} ...]'
        return argstr

    def _ctor(self) -> type:
        """ Return a callable that constructs any required objects from a single string argument. """
        tp = type(self.default)
        if tp in (bool, int, float):
            return tp
        return str

    def _multiargs(self) -> bool:
        """ If True, multiple command-line arguments should be combined into a list. """
        return isinstance(self.default, list)


class _CmdlineHelp(_CmdlineArgument):
    """ Generates command-line usage messages and argument help strings. """

    keys = '-h', '--help'
    desc = "Show this help message and exit."

    def __init__(self, opts:Iterable[_CmdlineArgument], script="", description="", *, out=sys.stdout) -> None:
        self._opts = opts                # Iterable of options to format.
        self._script = script            # Program script name as run in the command line.
        self._description = description  # A short description of what the program does.
        self._out = out                  # Output stream for help text.

    def __call__(self, *args) -> None:
        """ Disregard any arguments. Get the formatted text, write it to the stream, and exit the program. """
        text = self._format_help()
        self._out.write(text)
        sys.exit(0)

    def _format_help(self) -> str:
        """ Format lines of info text for all options sorted by string key and return a single string. """
        items = []
        opts = sorted(self._opts, key=str)
        headers = [*map(str, opts)]
        # Add the program description as a title if given.
        title = self._description
        if title:
            items += title.strip(), '\n'
        # Add a usage string if a program script is given.
        script = self._script
        if script:
            items += ['usage: ', os.path.basename(script)]
            for h in headers:
                items += ' [', h, ']'
            items.append('\n')
        # Add one or two lines of help for every available option.
        if items:
            items.append('\n')
        max_header_width = 32
        col_width = max([w for w in map(len, headers) if w < max_header_width]) + 2
        for option, header in zip(opts, headers):
            desc = option.desc
            if desc:
                if len(header) <= col_width:
                    header = header.ljust(col_width)
                else:
                    header += '\n    '
                items += header, desc, '\n'
        return ''.join(items)


class CmdlineParser:
    """ Command line option namespace/parser for the Spectra program. """

    def __init__(self) -> None:
        self._attrs_by_opt = {}  # Attribute names keyed by the options that affect them.
        self._opts_by_key = {}   # Dict of options by string key. An option may have more than one key.
        self._extra_args = []    # List of args that did not find matches during parsing.

    def add_option(self, attr:str, opt:_CmdlineArgument):
        """ Add an option to the attr dict, then to the key dict under every key. """
        self._attrs_by_opt[opt] = attr
        for k in opt.keys:
            self._opts_by_key[k] = opt

    def add_help(self, *args) -> None:
        """ Add a special object for formatting option help. The attribute is just a dummy name. """
        help_opt = _CmdlineHelp(self._attrs_by_opt, *args)
        self.add_option("_HELP_OPT", help_opt)

    def parse(self, argv:Iterable[str]) -> dict:
        """
        Parse arguments into a dict of options and save any leftovers to a list.
        Option keys must be prefixed by at least one '-', and its arguments (if any) follow it after '='
        Any args before the first prefixed option are ignored (i.e. put straight into extras).
        After that, arguments belonging to each option are delimited by spaces:

          ignored  ignored            3 args                          1 arg
        |*********| |**| [ key ] |---------------| [  key  ] [  key  ] |-|
        program.exe mode --files=a.txt b.txt c.txt --verbose --timeout=300

        """
        d = {}
        groups = []
        last_group = self._extra_args
        for s in argv:
            if s.startswith('-'):
                last_group = []
                groups.append(last_group)
            last_group.append(s)
        for group in groups:
            s, *args = group
            k, *eq = s.split('=')
            opt = self._opts_by_key.get(k)
            if opt is None:
                self._extra_args += group
            else:
                attr = self._attrs_by_opt[opt]
                d[attr] = opt(*eq, *args)
        return d

    def get_extras(self) -> List[str]:
        """ Return all unmatched arguments left over from parsing operations. """
        return self._extra_args[:]


class CmdlineOptionNamespace:
    """
    Namespace for CmdlineOption objects which are declared in the class body like this:

    test_option: str = CmdlineOption("--test", "default value", "Namespace test option")

    When parsed, arguments that match valid options are saved as instance attributes.
    Unmatched options will fall back to the class attributes, which return default values.

    Declaring options this way ensures that linters know each option is a valid attribute,
    but the type annotation may be necessary to keep them from complaining about the type.
    """

    def __init__(self, app_description="No description.") -> None:
        self._app_description = app_description  # Description shown in command-line help.

    def parse(self, argv:Iterable[str]=None) -> None:
        """ Create a parser object, load command line options, and parse them into instance attributes.
            Arguments are taken from <argv> if provided, otherwise from sys.argv. """
        parser = CmdlineParser()
        for tp in self.__class__.__mro__[::-1]:
            for attr, item in vars(tp).items():
                if isinstance(item, CmdlineOption):
                    parser.add_option(attr, item)
        parser.add_help(sys.argv[0], self._app_description)
        if argv is None:
            argv = sys.argv[1:]
        opt_dict = parser.parse(argv)
        self.__dict__.update(opt_dict)
