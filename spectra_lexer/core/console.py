""" Contains useful types for introspection and/or interactive interpreter operations. """

from code import InteractiveConsole
from functools import partial, update_wrapper
import sys
from typing import Callable


class HelpWrapper(partial):
    """ A function wrapped to display helpful information on repr() and help(). """

    __help__: str  # String shown on repr() and in place of ordinary help.

    def __new__(cls, func:Callable):
        """ Add help using the name, annotations, and/or docstring of the function. """
        self = super().__new__(cls, func)
        update_wrapper(self, func)
        lines = [f"COMMAND: {self.__name__}", ""]
        if hasattr(self, "__annotations__"):
            params = dict(self.__annotations__)
            ret = params.pop("return", "<unknown>")
            p = "ACCEPTS - "
            if not params:
                lines.append(f"{p}no arguments")
            for k, v in params.items():
                lines.append(f"{p}{k}: {cls._short_type_name(v)}")
                p = " " * len(p)
            lines += ["", f"RETURNS -> {cls._short_type_name(ret)}", ""]
        if hasattr(self, "__doc__"):
            lines.append(self.__doc__)
        self.__help__ = "\n".join(lines)
        return self

    def __repr__(self) -> str:
        return self.__help__

    @staticmethod
    def _short_type_name(cls:type) -> str:
        """ Return the name of a type without all the annoying prefixes on generic type aliases. """
        return getattr(cls, '__name__', str(cls)).replace("typing.","")


class xhelp:
    """ You asked for help on help, didn't you? Boredom has claimed yet another victim.
        This object overrides the builtin 'help', which breaks custom Python consoles. """

    _HELP_SECTIONS = [lambda x: [f"OBJECT - {x!r}"],
                      lambda x: [f"  TYPE - {type(x).__name__}"],
                      lambda x: ["----------ATTRIBUTES----------",
                                 ', '.join([k for k in dir(x) if not k.startswith('_')]) or "None"],
                      lambda x: ["-------------INFO-------------",
                                 *map(str.lstrip, str(x.__doc__).splitlines())]]

    def __call__(self, *args:object) -> None:
        if not args:
            print(self)
        for obj in args:
            print("")
            if hasattr(obj, "__help__"):
                print(obj.__help__)
            else:
                for fn in self._HELP_SECTIONS:
                    try:
                        for line in fn(obj):
                            print(line)
                    except (AttributeError, TypeError, ValueError):
                        continue
            print("")

    def __repr__(self) -> str:
        return "Type help(object) for auto-generated help on any Python object."


class AttrRedirector:
    """ Context manager that temporarily overwrites a number of attributes on a target object, then restores them.
        Only works on objects with a __dict__. The usual case is redirecting streams and hooks from the sys module. """

    def __init__(self, target:object, **attrs):
        """ We usually have specific literal attributes to redirect, so **keywords are best. """
        self._params = vars(target), attrs

    def __exit__(self, *args) -> None:
        """ Switch the attributes on both dicts. This operation is symmetrical and works for __enter__ as well. """
        d, attrs = self._params
        for a in attrs:
            d[a], attrs[a] = attrs[a], d[a]

    __enter__ = __exit__


class SystemConsole:
    """ Component for system interpreter operations using engine commands. """

    ps1 = ps2 = ""                   # Interactive mode prompt strings.
    interpreter: InteractiveConsole  # Interactive interpreter. Evaluates text input.
    write_callback: Callable         # Callback to send text output.

    def __init__(self, write_callback:Callable, interactive:bool=True, locals_ns=None):
        """ If interactive mode is requested, enable the prompts and write an opening message. """
        self.interpreter = InteractiveConsole(locals_ns)
        self.write_callback = write_callback
        if interactive:
            self.ps1 = ">>> "  # Standard input prompt.
            self.ps2 = "... "  # Input prompt when more lines are needed.
            self.write(f"Spectra Console - Python {sys.version}\n"
                       f"Type 'dir()' to see a list of engine commands and other globals.\n{self.ps1}")

    def run(self, text_in:str) -> None:
        """ When a new line is sent, push it to the interpreter and run it if it makes a complete statement.
            Redirect the standard output streams to our write method during execution. """
        with AttrRedirector(sys, stdout=self, stderr=self):
            try:
                more = self.interpreter.push(text_in)
            except KeyboardInterrupt:
                self.write("KeyboardInterrupt\n")
            self.write(self.ps2 if more else self.ps1)

    def write(self, text_out:str) -> None:
        """ Forward all output text to the callback as well as stdout. """
        sys.__stdout__.write(text_out)
        sys.__stdout__.flush()
        self.write_callback(text_out)
