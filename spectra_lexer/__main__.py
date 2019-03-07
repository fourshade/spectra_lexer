import sys
from time import time

from PyQt5.QtWidgets import QDialog

from spectra_lexer import core, gui_qt, interactive, plover
from spectra_lexer.app import Application


_ENTRY_POINTS = {}
def entry_point(func):
    """ Decorator for a console script entry point. """
    _ENTRY_POINTS[func.__name__] = func
    return func


@entry_point
def batch():
    """ Top-level function for operation of the Spectra program by itself in batch mode.
        The script will exit after processing all translations and saving the rules. """
    s_time = time()
    app = Application(core)
    app.start()
    # Run the lexer in parallel on all translations, save the results, and print the execution time.
    results = app.call("lexer_query_map")
    app.call("rules_save", results)
    print(f"Processing done in {time() - s_time:.1f} seconds.")


@entry_point
def gui():
    """ Top-level function for operation of the Spectra program *by itself* with the standard GUI. """
    # Assemble and start all components. The GUI components must be first in the list so that they start before others.
    app = Application(gui_qt, core, interactive)
    app.start()


@entry_point
def plover_test():
    """ Entry point for testing the Plover plugin by running it with no engine in a standalone configuration. """
    PloverDialog()


class PloverDialog(QDialog):
    """ Main entry point for the Plover plugin. Non-instantiatable dummy class with parameters required by Plover.
        The actual window returned by __new__ is the standard QMainWindow used by the standalone GUI.
        This class is just a facade, appearing as a QDialog to satisfy Plover's setup requirements. """

    # Class constants required by Plover for toolbar.
    TITLE = 'Spectra'
    ICON = ':/spectra_lexer/icon.svg'
    ROLE = 'spectra_dialog'
    SHORTCUT = 'Ctrl+L'

    # Docstring is used as tooltip on Plover GUI toolbar, so change it dynamically.
    __doc__ = "See the breakdown of words using steno rules."

    # The window and all of its contents are destroyed if it is closed with no referents.
    # The app's components are relatively expensive to create, so an app reference is kept
    # in the class dictionary and returned on every call after the first, making it a singleton.
    window = None

    def __new__(cls, engine=None, *args):
        """ Only create a new app/window instance on the first call; return the saved instance otherwise. """
        if cls.window is None:
            app = Application(gui_qt, plover, core, interactive)
            # The engine is always the first argument passed by Plover. Others are irrelevant.
            # In plugin mode, the GUI event loop isn't run by Spectra, so the Qt window is returned instead.
            cls.window = app.start()
            app.call("plover_test") if engine is None else app.call("new_plover_engine", engine)
        return cls.window


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
