""" Module for user-configurable command-line options. """

import os
import sys
from typing import Any, Iterable, Iterator, List


class CmdlineArgument:
    """ Abstract class for information about a single argument from the command line. """

    def __call__(self, *args:str) -> Any:
        """ Return a final value for this option based on zero or more argument strings. """
        raise NotImplementedError

    def __iter__(self) -> Iterator[str]:
        """ Yield all unique command-line option strings that cause this action. """
        raise NotImplementedError

    def usage(self) -> str:
        """ Return a usage string for this option based on its keys. """
        return "|".join(self)

    def description(self) -> str:
        """ Return a help string describing this argument. """
        raise NotImplementedError


class CmdlineOption(CmdlineArgument):
    """ A command-line option corresponding to a single object which can be placed in an attribute. """

    def __init__(self, key:str, desc="No description.", opt_type=str) -> None:
        self._key = key            # Option key (generally the name prefixed with --).
        self._desc = desc          # Optional description to be displayed in help.
        self._opt_type = opt_type  # Data type to be produced if the option is specified.

    def _multiargs(self) -> bool:
        """ If True, multiple command-line arguments should be combined in a string collection. """
        return issubclass(self._opt_type, (tuple, list, set))

    def __call__(self, *args:str) -> Any:
        """ Convert argument strings to the type required by this option and return it.
            Usually this is a single value, but multiargs types will produce a collection. """
        if self._multiargs():
            return self._opt_type(args)
        if len(args) != 1:
            raise ValueError(f'Option {self._key} takes exactly one argument, got {len(args)}.')
        return self._opt_type(*args)

    def __iter__(self) -> Iterator[str]:
        yield self._key

    def usage(self) -> str:
        if self._multiargs():
            argstr = '<str> [<str> ...]'
        else:
            argstr = '<' + self._opt_type.__name__ + '>'
        return super().usage() + '=' + argstr

    def description(self) -> str:
        return self._desc


class CmdlineHelp(CmdlineArgument):
    """ Generates command-line usage messages and argument help strings. """

    def __init__(self, opts:Iterable[CmdlineArgument], script_name:str, description:str,
                 *, file=None, max_col_width=32) -> None:
        self._opts = [*opts, self]           # Options to format (including this one).
        self._script_name = script_name      # Program name as run from the command line.
        self._description = description      # A short description of what the program does.
        self._file = file or sys.stdout      # Output stream for help text (standard output by default).
        self._max_col_width = max_col_width  # Maximum width of keys column in characters.

    def _usage_line(self) -> str:
        # Return a usage string, starting with the program script name.
        segments = ['usage: ', self._script_name]
        for opt in self._opts:
            segments += ' [', opt.usage(), ']'
        return "".join(segments)

    def _info_lines(self) -> Iterator[str]:
        """ Yield one or two lines of specific info for every available option. """
        keylists = [", ".join(opt) for opt in self._opts]
        col_width = max([w for w in map(len, keylists) if w < self._max_col_width]) + 2
        for opt, keys in zip(self._opts, keylists):
            desc = opt.description()
            if len(keys) <= col_width:
                yield keys.ljust(col_width) + desc
            else:
                yield keys
                yield '    ' + desc

    def _format_help(self) -> str:
        """ Format all help text and return a single string. """
        lines = [self._description,
                 self._usage_line(),
                 "",
                 *self._info_lines(),
                 ""]
        return '\n'.join(lines)

    def __call__(self, *args) -> None:
        """ Disregard any arguments. Get the formatted text, write it to the stream, and exit the program. """
        text = self._format_help()
        self._file.write(text)
        sys.exit(0)

    def __iter__(self) -> Iterator[str]:
        yield '-h'
        yield '--help'

    def description(self) -> str:
        return "Show this help message and exit."


class CmdlineParser:
    """ Command line option namespace/parser for the Spectra program. """

    def __init__(self) -> None:
        self._attrs_by_opt = {}  # Attribute names keyed by the options that affect them.
        self._opts_by_key = {}   # Dict of options by string key. An option may have more than one key.
        self._extra_args = []    # List of args that did not find matches during parsing.

    def add_option(self, attr:str, opt:CmdlineArgument) -> None:
        """ Add an option to the attr dict, then to the key dict under every key. """
        self._attrs_by_opt[opt] = attr
        for k in opt:
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


class CmdlineOptions:
    """ Namespace class for CmdlineOption objects. Option values are accessed as instance attributes.
        Unparsed options will fall back to default values. """

    def __init__(self, app_description="Command line application.") -> None:
        self._app_description = app_description  # App description shown in command-line help.
        self._options = {}  # Contains all option objects keyed by their destination attributes.

    def __getattr__(self, name:str) -> Any:
        raise AttributeError(f'"{name}" is not the name of a valid command-line option.')

    def add(self, name:str, default:Any=None, desc="No description.") -> None:
        """ Add a new option and set its attribute to be the default value (until parsed).
            Since attribute names cannot have hyphens, they are replaced with underscores. """
        key = "--" + name
        opt_type = str if default is None else type(default)
        opt = CmdlineOption(key, desc, opt_type)
        attr_name = name.replace("-", "_")
        self._options[attr_name] = opt
        setattr(self, attr_name, default)

    def parse(self, argv:Iterable[str]=None) -> None:
        """ Create a parser object, load command line options, and parse them into instance attributes.
            Arguments are taken from <argv> if provided, otherwise from sys.argv. """
        parser = CmdlineParser()
        for attr, item in self._options.items():
            parser.add_option(attr, item)
        script, *argv = (argv or sys.argv)
        if script:
            script = os.path.basename(script)
        # Add a special object for formatting option help. The attribute is just a dummy name.
        help_opt = CmdlineHelp(self._options.values(), script, self._app_description)
        parser.add_option("_HELP_OPT", help_opt)
        opt_dict = parser.parse(argv)
        self.__dict__.update(opt_dict)
