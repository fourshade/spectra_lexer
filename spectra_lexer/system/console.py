""" Contains useful types for introspection and/or interactive interpreter operations. """

from code import InteractiveConsole
import sys
from typing import Callable


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
    write_callback: Callable         # Optional callback to send text output.

    def __init__(self, locals_ns:dict=None, write_to:Callable=None):
        """ Set the write callback and write an opening message before input begins. """
        self.interpreter = InteractiveConsole(locals_ns)
        self.write_callback = write_to
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
        """ Forward all output text to stdout, as well as the callback if one was given. """
        sys.__stdout__.write(text_out)
        sys.__stdout__.flush()
        write_cb = self.write_callback
        if write_cb is not None:
            write_cb(text_out)
