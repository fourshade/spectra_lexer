""" Module for user-configurable command-line options. """

import os
import sys
from typing import Any, Callable, Iterable, Mapping, List, Sequence


class CmdlineArgument:
    """ Abstract class for information about a single argument from the command line. """

    keys: Sequence[str]  # Contains all unique command-line option strings that cause this action.
    desc: str            # The help string describing the argument.

    def __call__(self, *args:str) -> Any:
        """ An option will return a value based on zero or more argument strings. """
        raise NotImplementedError

    def __str__(self) -> str:
        """ Return a usage string for this option based on its keys. """
        return "|".join(self.keys)


class CmdlineOption(CmdlineArgument):
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


class CmdlineHelp(CmdlineArgument):
    """ Generates command-line usage messages and argument help strings. """

    keys = '-h', '--help'
    desc = "Show this help message and exit."

    max_header_width = 32

    def __init__(self, opts:Iterable[CmdlineArgument], script_name="", description="", *, out=sys.stdout) -> None:
        self._opts = opts                # Iterable of options to format.
        self._script_name = script_name  # Program name as run from the command line.
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
        headers = list(map(str, opts))
        # Add the program description as a title if given.
        title = self._description.strip()
        if title:
            items += [title, '\n']
        # Add a usage string, with the program script name if given.
        script = self._script_name
        if script:
            items += ['usage: ', script]
        else:
            items.append('options:')
        for h in headers:
            items += ' [', h, ']'
        items.append('\n\n')
        # Add one or two lines of help for every available option.
        col_width = max([w for w in map(len, headers) if w < self.max_header_width]) + 2
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

    def add_option(self, attr:str, opt:CmdlineArgument) -> None:
        """ Add an option to the attr dict, then to the key dict under every key. """
        self._attrs_by_opt[opt] = attr
        for k in opt.keys:
            self._opts_by_key[k] = opt

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
    Base namespace class for CmdlineOption objects which are declared in the class body like this:

    test_option: str = CmdlineOption("--test", "default value", "Namespace test option")

    When parsed, arguments that match valid options are saved as instance attributes.
    Unmatched options will fall back to the class attributes, which return default values.

    Declaring options this way ensures that linters know each option is a valid attribute,
    but the type annotation may be necessary to keep them from complaining about the type.
    """

    def parse_options(self, argv:Iterable[str]=None, *, app_description:str=None) -> None:
        """ Create a parser object, load command line options, and parse them into instance attributes.
            Arguments are taken from <argv> if provided, otherwise from sys.argv.
            If an <app_description> is given, command-line help will be shown on -h with that description. """
        parser = CmdlineParser()
        options = self.get_options()
        for attr, item in options.items():
            parser.add_option(attr, item)
        script, *argv = (argv or sys.argv)
        if script:
            script = os.path.basename(script)
        # Add a special object for formatting option help. The attribute is just a dummy name.
        help_opt = CmdlineHelp(options.values(), script, app_description or str(self.__doc__))
        parser.add_option("_HELP_OPT", help_opt)
        opt_dict = parser.parse(argv)
        self.__dict__.update(opt_dict)

    @classmethod
    def get_options(cls) -> dict:
        """ Find the command line options for each class in the MRO. """
        return {attr: item
                for tp in cls.__mro__[::-1]
                for attr, item in vars(tp).items()
                if isinstance(item, CmdlineOption)}


class EntryPoint:
    """ Entry point for an application. Modules are imported as needed to avoid loading unnecessary dependencies. """

    def __init__(self, module_name:str, func_name:str, description="Unknown function.") -> None:
        self._module_name = module_name  # Full name of module to import.
        self._func_name = func_name      # Name of callable to execute in the module.
        self._description = description  # Textual description when the user looks for help.

    def __call__(self, *args, **kwargs) -> int:
        """ Import the module, call the named function, and return the result (usually an exit code). """
        attr = self._func_name
        module = __import__(self._module_name, fromlist=[attr])
        func = getattr(module, attr)
        return func(*args, **kwargs)

    def __str__(self) -> str:
        return self._description


class EntryPointSelector:
    """ Chooses entry points using the first command-line argument as a "mode" string. """

    def __init__(self, entry_points:Mapping[str, EntryPoint], *, default_mode:str=None) -> None:
        self._entry_points = entry_points  # Mapping of application entry points by mode.
        self._default_mode = default_mode  # Default mode string (optional, used when no mode is given).

    def load(self, mode="") -> Callable[..., int]:
        """ Make sure <mode> matches exactly one entry point callable, then import and return it. """
        matches = self._match(mode)
        if len(matches) == 1:
            return matches[0]
        # If there was no acceptable match, return a callable to print all available modes and descriptions.
        if matches:
            error_msg = f'Operation "{mode}" has multiple matches. Use more characters.'
        elif not mode:
            error_msg = 'An operation mode is required as the first command-line argument.'
        else:
            error_msg = f'No matches for operation "{mode}".'
        return self._error_main(error_msg)

    def _match(self, mode="") -> List[Callable]:
        """ Get all entry points that match a <mode> string up to its last character.
            With no mode argument (or a blank one), redirect to the default mode. """
        if not mode:
            if not self._default_mode:
                return []
            mode = self._default_mode
        return [ep for k, ep in self._entry_points.items() if k.startswith(mode)]

    def _error_main(self, error_msg:str) -> Callable[[], int]:
        """ Return a main callable that prints lines of entry point info and returns an error code. """
        def print_error() -> int:
            print(error_msg)
            print('Currently available operations:')
            for k, ep in self._entry_points.items():
                print(f"{k} - {ep}")
            return -1
        return print_error

    def main(self) -> int:
        """ Run an entry point using the first command-line argument as the mode. """
        return self._main(*sys.argv)

    def _main(self, script="", mode="", *argv:str) -> int:
        """ Look up the entry point under <mode>, call it without it, and return the exit code. """
        func = self.load(mode)
        sys.argv = [script, *argv]
        return func()
