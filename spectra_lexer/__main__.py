""" Master console script for the Spectra program. Contains all entry points. """

import sys

from spectra_lexer import batch, core, gui_qt, interactive, plover
from spectra_lexer.app import Application


_ENTRY_POINTS = {}
def entry_point(func):
    """ Decorator for a console script entry point. """
    _ENTRY_POINTS[func.__name__] = func
    return func


@entry_point
def analyze():
    """ Top-level function for operation of the Spectra program by itself in batch mode.
        The script will exit after processing all translations and saving the rules. """
    app = Application(core, batch)
    app.start()


@entry_point
def gui():
    """ Top-level function for operation of the Spectra program *by itself* with the standard GUI. """
    # Assemble and start all components. The GUI components must be first in the list so that they start before others.
    app = Application(gui_qt, core, interactive)
    app.start()


@entry_point
class PloverPlugin:
    """ See the breakdown of words using steno rules. """

    # Class constants required by Plover for toolbar.
    TITLE = 'Spectra'
    ICON = ':/spectra_lexer/icon.svg'
    ROLE = 'spectra_dialog'
    SHORTCUT = 'Ctrl+L'

    def __new__(cls, *args):
        """ Entry point for the Plover plugin. Running it with no args starts a standalone test configuration. """
        app = Application(gui_qt, plover, core, interactive)
        return app.start(plugin_args=args)


def main():
    """ Main console entry point for the Spectra steno lexer. """
    script, *args = sys.argv
    # The first argument determines the entry point/mode to run.
    # All subsequent arguments are command-line options for that mode.
    # With no arguments, redirect to the standalone GUI app.
    mode, *cmd_opts = args or ["gui"]
    # Make sure the mode matches exactly one entry point function.
    matches = [func for attr, func in _ENTRY_POINTS.items() if attr.startswith(mode)]
    if not matches:
        print(f'No matches for operation "{mode}"')
        return
    if len(matches) > 1:
        print(f'Multiple matches for operation "{mode}". Use more characters.')
        return
    # Reassign the remaining arguments to sys.argv and run the entry point.
    sys.argv = [script, *cmd_opts]
    matches[0]()


if __name__ == '__main__':
    main()
