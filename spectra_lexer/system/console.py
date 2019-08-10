""" Contains useful types for introspection and/or interactive interpreter operations. """

from code import InteractiveConsole
import inspect
import sys
from typing import Callable


class xhelp:
    """ You asked for help on help, didn't you? Boredom has claimed yet another victim.
        This object overrides the builtin 'help', which breaks custom Python consoles. """

    _HELP_SECTIONS = [lambda x: [f"OBJECT - {x!r}"],
                      lambda x: [f"  TYPE - {type(x).__name__}"],
                      lambda x: ["----------SIGNATURE----------",
                                 inspect.signature(x)],
                      lambda x: ["----------ATTRIBUTES----------",
                                 ', '.join([k for k in dir(x) if not k.startswith('_')]) or "None"],
                      lambda x: ["-------------INFO-------------",
                                 *map(str.lstrip, str(x.__doc__).splitlines())]]

    def __call__(self, *args:object, write:Callable=print) -> None:
        """ Write each help section that doesn't raise an exception, in order. """
        if not args:
            write(self)
        for obj in args:
            write("")
            for fn in self._HELP_SECTIONS:
                try:
                    for line in fn(obj):
                        write(line)
                except Exception:
                    # Arbitrary objects may raise arbitrary exceptions. Just skip sections that don't behave.
                    continue
            write("")

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
    """ Component for interactive system interpreter operations. """

    ps1: str = ">>> "                # Standard input prompt.
    ps2: str = "... "                # Input prompt when more lines are needed.
    interpreter: InteractiveConsole  # Interactive interpreter. Evaluates text input.

    def __init__(self, locals_ns:dict=None, *, write_to:Callable=None, **kwargs):
        """ Add the help function, set the write callback and write an opening message before input begins. """
        locals_ns.update(kwargs, help=xhelp())
        self.interpreter = InteractiveConsole(locals_ns)
        if write_to is not None:
            self.write = write_to
        self.write(f"Spectra Console - Python {sys.version}\n"
                   f"Type 'dir()' to see a list of application components and other globals.\n{self.ps1}")

    def __call__(self, text_in:str) -> None:
        """ When a new line is sent, push it to the interpreter and run it if it makes a complete statement.
            Redirect the standard output streams to our write method during execution. """
        with AttrRedirector(sys, stdout=self, stderr=self):
            try:
                more = self.interpreter.push(text_in)
            except KeyboardInterrupt:
                self.write("KeyboardInterrupt\n")
            self.write(self.ps2 if more else self.ps1)

    def write(self, text_out:str) -> None:
        """ Forward all output text to stdout by default. """
        sys.__stdout__.write(text_out)
        sys.__stdout__.flush()
