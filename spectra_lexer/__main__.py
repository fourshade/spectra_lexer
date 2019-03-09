""" Master console script for the Spectra program. Contains all entry points. """

import sys

from spectra_lexer import batch, core, gui_qt, plover, steno, tools, Component
from spectra_lexer.app import Application
from spectra_lexer.steno import SearchEngine
from spectra_lexer.tools import FileDialogTool


class EntryPoint:
    """ Wrapper for a console script entry point. Keywords are assigned to the entry point object as attributes.
        Arguments may include component classes and modules. Adding a component class already present removes it. """
    def __init__(self, *modules, **attrs):
        """ Unpack all component classes found in modules. """
        self.__dict__ = attrs
        self.classes = [cls for m in modules for cls in (m, *vars(m).values())
                        if isinstance(cls, type) and issubclass(cls, Component)]

    def __call__(self, *args):
        """ Assemble and start all components. """
        return Application(*self.classes).start(*args)


# Run the Spectra program by itself in batch mode.
analyze = EntryPoint(batch, core, steno, SearchEngine)
# Run the Spectra program by itself with the standard GUI. The GUI should start first for smoothest operation.
gui = EntryPoint(gui_qt, tools, core, steno)
# Run the Spectra program as a plugin for Plover. Running it with no args starts a standalone test configuration.
plugin = EntryPoint(plover, gui_qt, tools, FileDialogTool, core, steno,
                    # Class constants required by Plover for toolbar.
                    __doc__='See the breakdown of words using steno rules.',
                    TITLE='Spectra',
                    ICON=':/spectra_lexer/icon.svg',
                    ROLE='spectra_dialog',
                    SHORTCUT='Ctrl+L')


def main():
    """ Main console entry point for the Spectra steno lexer. """
    script, *args = sys.argv
    # The first argument determines the entry point/mode to run.
    # All subsequent arguments are command-line options for that mode.
    # With no arguments, redirect to the standalone GUI app.
    mode, *cmd_opts = args or ["gui"]
    # Make sure the mode matches exactly one entry point function.
    matches = [ep for attr, ep in globals().items() if attr.startswith(mode) and isinstance(ep, EntryPoint)]
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
