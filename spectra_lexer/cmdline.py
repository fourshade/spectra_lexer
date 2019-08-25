import sys
from typing import Any, Dict, Iterable, Iterator, List, Sequence


class _BaseOption:
    """ Abstract class for information about a single argument from the command line. """

    keys: Sequence[str]  # Contains all unique command-line option strings that cause this action.
    desc: str = ""       # The help string describing the argument. If there is no description, just leave it blank.

    def __call__(self, key:str, *args:str) -> Any:
        """ An option has an effect on an attribute dict based on zero or more argument strings. """
        raise NotImplementedError

    def __str__(self) -> str:
        """ Return a short usage string for this option. """
        return "|".join(self.keys)

    def __lt__(self, other) -> bool:
        """ Options are ordered by their first key (which should be unique to each one). """
        return self.keys[0] < other.keys[0]


class _HelpOption(_BaseOption):
    """ Formatter for generating usage messages and argument help strings. """

    keys = ('--help',)
    desc = "Show this help message and exit."
    _opts: Iterable[_BaseOption]
    _prog: str         # Name of the program as run in the command line.
    _description: str  # A description of what the program does.

    def __init__(self, opts:Iterable[_BaseOption], progname:str="", description:str="") -> None:
        self._opts = opts
        self._prog = progname
        self._description = (description + '\n') if description else ""

    def __call__(self, *args, max_header_width:int=32, file=sys.stdout) -> None:
        headers = [*map(str, self._opts)]
        col_width = max([w for w in map(len, headers) if w < max_header_width]) + 2
        items = ['usage: ', self._prog]
        for h in headers:
            items += ' [', h, ']'
        items += '\n', self._description, '\n'
        for option, header, in zip(self._opts, headers):
            desc = option.desc
            if desc:
                if len(header) <= col_width:
                    items += header.ljust(col_width), desc, '\n'
                else:
                    items += header, '\n    ', desc, '\n'
        file.write(''.join(items))
        sys.exit(0)


class Option(_BaseOption):
    """ An option corresponding to a single object which can be placed in an attribute. """

    _default: Any             # The value to be produced if the option is not specified.
    _ctor: type = str         # A callable that constructs the required object from a single string argument.
    _multiargs: bool = False  # If True, multiple command-line arguments should be combined into a list.

    def __init__(self, key:str, default:Any=None, desc:str="") -> None:
        self.keys = [key]
        self.desc = desc
        self._default = default
        tp = type(default)
        if tp in (bool, int, float):
            self._ctor = tp
        elif tp is list:
            self._multiargs = True

    def __call__(self, key:str, *args:str) -> Any:
        """ nargs=None will produce a single value. nargs+ will produce a list, even with only one value. """
        value = [*map(self._ctor, args)]
        if not self._multiargs:
            if len(value) != 1:
                raise ValueError(f'Option {key} takes exactly one argument, got {len(value)}.')
            value = value[0]
        return value

    def get_default(self) -> Any:
        return self._default

    def __str__(self) -> str:
        """ General argument format is --long=ARGS. """
        s = "|".join(self.keys)
        metavar = f'<{self._ctor.__name__}>'
        argstr = f'{s}={metavar}'
        if self._multiargs:
            argstr += f' [{metavar} ...]'
        return argstr


class _OptionParser:
    """ Tracks command-line options by their string keys. An option may have more than one key. """

    _attrs_by_opt: Dict[_BaseOption, str]  # Attribute names keyed by the options that affect them.
    _opts_by_key: Dict[str, _BaseOption]

    def __init__(self, *args) -> None:
        """ There is a special help object that does not need an attribute. Make it under a dummy name. """
        self._attrs_by_opt = {}
        self._opts_by_key = {}
        self['_HELP'] = _HelpOption(self, *args)

    def __iter__(self) -> Iterator[_BaseOption]:
        """ Iterate over all unique options sorted by key. """
        return iter(sorted(self._attrs_by_opt))

    def __setitem__(self, attr:str, option:_BaseOption) -> None:
        """ Add this option to the dict under every key. """
        self._attrs_by_opt[option] = attr
        for k in option.keys:
            self._opts_by_key[k] = option

    def parse(self, argv:Iterable[str]) -> tuple:
        """ Parse options into an attribute dict and a leftovers list.
            Any args before the first prefixed option are ignored. """
        d = {}
        extras = []
        groups = [extras]
        for s in argv:
            if s.startswith('-'):
                groups.append([])
            groups[-1].append(s)
        for group in groups[1:]:
            s, *args = group
            k, *eq = s.split('=')
            opt = self._opts_by_key.get(k)
            if opt is None:
                extras += group
            else:
                attr = self._attrs_by_opt[opt]
                d[attr] = opt(k, *eq, *args)
        return d, extras


class OptionNamespace:
    """ Command line option namespace/parser for the Spectra program. """

    _parser: _OptionParser  # Main parser implementation. Stores all found options.

    def __init__(self, progname:str="", description:str="") -> None:
        """ Analyze our class hierarchy for options, set their defaults, and add them to the parser. """
        self._parser = _OptionParser(progname, description)
        for attr in dir(self):
            item = getattr(self, attr)
            if isinstance(item, Option):
                setattr(self, attr, item.get_default())
                self._parser[attr] = item

    def parse(self, argv:Iterable[str]) -> List[str]:
        """ Parse options into the instance attribute dict and return only the leftover args. """
        d, argv = self._parser.parse(argv)
        vars(self).update(d)
        return argv
