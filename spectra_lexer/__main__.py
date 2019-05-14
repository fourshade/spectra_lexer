""" Master console script and primary entry point for the Spectra program. """

import sys
from typing import List, Type

from spectra_lexer.core import COREApp
from spectra_lexer.gui_qt.app import GUIQtApplication
from spectra_lexer.plover.app import PloverPluginApplication
from spectra_lexer.steno.app import StenoConsoleApplication, StenoAnalyzeApplication, StenoIndexApplication

# Container for all app classes that qualify as entry points to the Spectra program.
ENTRY_POINTS = {"console": StenoConsoleApplication,
                "analyze": StenoAnalyzeApplication,
                "index":   StenoIndexApplication,
                "gui":     GUIQtApplication,
                "plugin":  PloverPluginApplication}


def _get_ep_matches(key:str) -> List[Type[COREApp]]:
    """ Get all entry points that match the given key up to its last character. """
    return [ep for mode, ep in ENTRY_POINTS.items() if mode.startswith(key)]


def _get_ep_help() -> List[str]:
    """ Get a list of help strings for each possible app invokation. """
    return [f"{mode} - {ep.DESCRIPTION}" for mode, ep in ENTRY_POINTS.items()]


def main(*args, default_mode:str="NULL") -> int:
    """ The first command-line argument determines the entry point/mode to run.
        All subsequent arguments are command-line options for that mode.
        With no arguments, redirect to the default entry point (if given).
        Any args given to this method are passed straight to the app constructor. """
    script, *cmd_args = sys.argv
    mode, *cmd_opts = cmd_args or [default_mode]
    # Make sure the mode matches exactly one entry point callable.
    matches = _get_ep_matches(mode)
    if not matches:
        # If nothing matches, display all app classes and their help strings.
        print(f'No matches for operation "{mode}". Currently available operations:')
        print("\n".join(_get_ep_help()))
        return -1
    if len(matches) > 1:
        print(f'Multiple matches for operation "{mode}". Use more characters.')
        return -1
    # Reassign the remaining arguments to sys.argv and run the app.
    sys.argv = [script, *cmd_opts]
    return matches[0](*args).run()


if __name__ == '__main__':
    # With no arguments, redirect to the standalone GUI app.
    sys.exit(main(default_mode="gui"))
