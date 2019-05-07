from code import InteractiveConsole
import sys
from typing import Callable


class AttrRedirector:
    """ Context manager that temporarily overwrites a number of attributes on a target object, then restores them.
        Only works on objects with a __dict__. The usual case is redirecting streams and hooks from the sys module. """

    _saved = {}

    def __init__(self, target:object, **attrs):
        self._attrs = attrs
        self._target_dict = target.__dict__

    def __enter__(self):
        self._saved = {a: self._target_dict[a] for a in self._attrs}
        self._target_dict.update(self._attrs)

    def __exit__(self, *args):
        self._target_dict.update(self._saved)


class SpectraConsole(InteractiveConsole):
    """ Interpreter console with redirectable output. """

    def __init__(self, d_locals:dict, output_cb:Callable):
        super().__init__(d_locals)
        self.write = output_cb
        self.redirector = AttrRedirector(sys, displayhook=self.display, stdout=self)

    def send(self, text_in:str) -> None:
        """ Process a line of input while redirecting the interactive display to our callback. """
        with self.redirector:
            self._send(text_in)

    def _send(self, text_in:str) -> None:
        """ When a command sends a new line of input, push to the console. """
        more = 0
        try:
            self.write(text_in + "\n")
            more = self.push(text_in)
        except KeyboardInterrupt:
            self.write("\nKeyboardInterrupt\n")
            self.resetbuffer()
        self.write("... " if more else ">>> ")

    def display(self, value:object) -> None:
        """ Like the normal console, show the repr of any return value on a new line, or nothing at all for None. """
        if value is not None:
            self.write(f"{value!r}\n")
        # Unlike the normal console, save the last value under _ in locals rather than globals.
        # It is too easy to step on other usages of _ (such as gettext) when saving to globals.
        self.locals["_"] = value
