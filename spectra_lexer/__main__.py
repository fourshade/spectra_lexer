""" Master console script for the Spectra program. Contains all entry points. """

import sys

from spectra_lexer.gui_qt import GUIQtApplication
from spectra_lexer.plover import PloverPluginApplication
from spectra_lexer.steno import StenoAnalyzeApplication, StenoIndexApplication


class Spectra:
    """ Container class for all entry points to the Spectra program, and the top-level class in the hierarchy. """
    @classmethod
    def get_ep_matches(cls, key):
        """ Get all entry points that match the given key up to its last character. """
        return [ep for attr, ep in vars(cls).items() if attr.startswith(key)]
    # Run the Spectra program by itself in batch mode. Interactive steno components are not required for this.
    analyze = StenoAnalyzeApplication
    index = StenoIndexApplication
    # Run the Spectra program by itself with the standard GUI. The GUI should start first for smoothest operation.
    gui = GUIQtApplication
    # Run the Spectra program as a plugin for Plover. Running it with no args starts a standalone test configuration.
    plugin = PloverPluginApplication


def main() -> int:
    """ Main console entry point for the Spectra steno lexer. """
    script, *args = sys.argv
    # The first argument determines the entry point/mode to run.
    # All subsequent arguments are command-line options for that mode.
    # With no arguments, redirect to the standalone GUI app.
    mode, *cmd_opts = args or ["gui"]
    # Make sure the mode matches exactly one entry point function.
    matches = Spectra.get_ep_matches(mode)
    if not matches:
        print(f'No matches for operation "{mode}"')
        return -1
    if len(matches) > 1:
        print(f'Multiple matches for operation "{mode}". Use more characters.')
        return -1
    # Reassign the remaining arguments to sys.argv and run the entry point.
    sys.argv = [script, *cmd_opts]
    return matches[0]().run()


if __name__ == '__main__':
    sys.exit(main())
