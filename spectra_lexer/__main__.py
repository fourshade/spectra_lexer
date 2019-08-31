#!/usr/bin/env python3

""" Master console script and primary entry point for the Spectra program. """

import sys
from typing import Callable, List, Optional


class EntryPoints:
    """ Formal entry point dictionary for applications.
        To avoid unnecessary imports (especially when dependencies are different), only strings are used here. """

    def __init__(self, *, default:str="") -> None:
        self._default = default  # Default entry point mode string (used when no mode is given at the command line).
        self._paths = {}         # Dict of all entry point module paths by mode.
        self._descriptions = []  # List of all description strings.

    def add(self, module_path:str, mode:str, desc:str="Unknown function.") -> None:
        """ At minimum, each entry point requires a module path string and a mode string.
            <module_path> is an absolute Python module path.
            <mode> refers to a callable member of that module, usually a class or function.
            The mode string is also used to choose that entry point from the command line.
            <desc> is shown beside each entry point when the user looks for help. """
        self._paths[mode] = module_path
        self._descriptions.append(f"{mode} - {desc}")

    def __call__(self, mode:str=None) -> Optional[Callable]:
        """ Make sure the mode matches exactly one entry point, then import and return it.
            With no mode argument (or a blank one), redirect to the default mode. """
        if not mode:
            mode = self._default
        matches = self._get_matches(mode)
        if len(matches) == 1:
            return self._import_callable(matches[0])
        # If there was no acceptable match, display a message, then show all available modes and description strings.
        if not mode:
            print('An operation mode is required as the first command-line argument.')
        elif not matches:
            print(f'No matches for operation "{mode}".')
        else:
            print(f'Operation "{mode}" has multiple matches. Use more characters.')
        print('Currently available operations:')
        print("\n".join(self._descriptions))

    def _get_matches(self, mode:str) -> List[Callable]:
        """ Get all entry point modes that match the given string up to its last character. """
        if not self._paths:
            raise RuntimeError('No entry points defined. Please check your imports.')
        return [k for k in self._paths if k.startswith(mode)]

    def _import_callable(self, mode:str) -> Callable:
        """ Import the module on the path corresponding to <mode>, then get the callable as an attribute. """
        module_path = self._paths[mode]
        module = __import__(module_path, globals(), locals(), [mode])
        return getattr(module, mode)


entry_points = EntryPoints(default="gui")
add = entry_points.add
add("spectra_lexer.app",      "console", "Run commands interactively from console.")
add("spectra_lexer.app",      "analyze", "Run the lexer on every item in a JSON steno translations dictionary.")
add("spectra_lexer.app",      "index",   "Analyze a translations file and index each one by the rules it uses.")
add("spectra_lexer.gui_http", "http",    "Run the application as an HTTP web server.")
add("spectra_lexer.gui_qt",   "gui",     "Run the application as a standalone GUI (default).")


def main(script:str="", mode:str="", *argv:str) -> int:
    """ Look up an entry point using the first command-line argument, call it with the rest, and return the exit code.
        If the return value isn't an integer, cast it to bool and return its inverse (so True is success). """
    func = entry_points(mode)
    if func is None:
        return -1
    result = func(script, *argv)
    if isinstance(result, int):
        return result
    return not result


if __name__ == '__main__':
    sys.exit(main(*sys.argv))
