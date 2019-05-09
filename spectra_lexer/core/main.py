import sys
from typing import Dict, List, Type

from spectra_lexer.core import Application


class Main:
    """ Primary entry point for programs with multiple modes. Parses the first command-line argument as a mode string.
        The mode is compared to a dict of app classes by prefix, the contents of which are displayed if none match. """

    _ep_dict: Dict[str, Type[Application]]  # Dict of (string: app_class) pairs to search as possible entry points.
    _default_mode: str  # Mode to use if no command-line arguments are given.

    def __init__(self, ep_dict:Dict[str, Type[Application]], default_mode:str= "NULL"):
        """ Use the given dict to find an entry point by key. """
        self._ep_dict = ep_dict
        self._default_mode = default_mode

    def _get_ep_matches(self, key:str) -> List[Type[Application]]:
        """ Get all entry points that match the given key up to its last character. """
        return [ep for mode, ep in self._ep_dict.items() if mode.startswith(key)]

    def _get_ep_help(self) -> List[str]:
        """ Get a list of help strings for each possible app invokation. """
        return [f"{mode} - {ep.DESCRIPTION}" for mode, ep in self._ep_dict.items()]

    def __call__(self, *args) -> int:
        """ The first argument determines the entry point/mode to run.
            All subsequent arguments are command-line options for that mode.
            With no arguments, redirect to the default entry point (if given).
            Any args given to this method are passed straight to the app constructor. """
        script, *cmd_args = sys.argv
        mode, *cmd_opts = cmd_args or [self._default_mode]
        # Make sure the mode matches exactly one entry point callable.
        matches = self._get_ep_matches(mode)
        if not matches:
            print(f'No matches for operation "{mode}". Currently available operations:')
            print("\n".join(self._get_ep_help()))
            return -1
        if len(matches) > 1:
            print(f'Multiple matches for operation "{mode}". Use more characters.')
            return -1
        # Reassign the remaining arguments to sys.argv and run the app.
        sys.argv = [script, *cmd_opts]
        return matches[0](*args).run()
