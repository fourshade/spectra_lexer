""" Module for dynamically importing program entry points. """

import sys
from typing import Callable, List, Mapping


def shift_argv() -> str:
    """ Return the first command-line argument after shifting its contents onto the script string.
        This has the effect of "consuming" it without affecting how the command line appears in help. """
    if len(sys.argv) < 2:
        return ""
    script, head, *tail = sys.argv
    sys.argv = [script + " " + head, *tail]
    return head


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

    def description(self) -> str:
        return self._description


class EntryPointSelector:
    """ Chooses entry points using the first command-line argument as a "mode" string. """

    def __init__(self, entry_points:Mapping[str, EntryPoint], *, default_mode:str=None) -> None:
        self._entry_points = entry_points  # Mapping of application entry points by mode.
        self._default_mode = default_mode  # Default mode string (optional, used when no mode is given).

    def _match(self, mode:str) -> List[EntryPoint]:
        """ Get all entry points that match a <mode> string up to its last character.
            With no mode argument (or a blank one), redirect to the default mode. """
        if not mode:
            if not self._default_mode:
                return []
            mode = self._default_mode
        return [ep for k, ep in self._entry_points.items() if k.startswith(mode)]

    def _info(self) -> List[str]:
        """ Return a list of lines with entry point info. """
        return [f"{k} - {ep.description()}" for k, ep in self._entry_points.items()]

    def _error_main(self, error_msg:str) -> Callable[..., int]:
        """ Return a main callable that prints lines of entry point info and returns an error code. """
        lines = [error_msg, '', 'Currently available operations:', *self._info()]
        def print_error(*args, **kwargs) -> int:
            for s in lines:
                print(s)
            return -1
        return print_error

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

    def main(self) -> int:
        """ Run an entry point using the first command-line argument as the mode. """
        mode = shift_argv()
        func = self.load(mode)
        return func()
