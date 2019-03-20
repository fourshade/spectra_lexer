""" Master console script for the Spectra program. Contains all entry points. """

import sys

from .app import BatchApplication, GUIQtApplication, PloverPluginApplication


class EntryPoint:
    """ Wrapper for a console script entry point. Keywords are assigned to the entry point object as attributes.
        Positional arguments will be added to those passed to run() by the caller. """
    def __init__(self, app_cls, args=(), desc=""):
        self.__dict__ = dict(app_cls.__dict__)
        self.app_cls = app_cls
        self.args = args

    def __call__(self, *args):
        """ Add arguments and start the application. """
        return self.app_cls().start(*self.args, *args)


class Spectra:
    """ Container class for all entry points to the Spectra program, and the top-level class in the hierarchy. """
    @classmethod
    def get_ep_matches(cls, key:str) -> list:
        """ Get all entry points that match the given key up to its last character. """
        return [ep for attr, ep in vars(cls).items() if attr.startswith(key)]
    # Run the Spectra program by itself in batch mode. Interactive steno components are not required for this.
    analyze = EntryPoint(BatchApplication, args=["lexer_query_all"],
                         desc="run the lexer on every item in a JSON steno translations dictionary.")
    index = EntryPoint(BatchApplication, args=["index_generate"],
                       desc="analyze a translations file and index each translation by the rules it uses.")
    # Run the Spectra program by itself with the standard GUI. The GUI should start first for smoothest operation.
    gui = EntryPoint(GUIQtApplication, desc="run the interactive GUI application by itself.")
    # Run the Spectra program as a plugin for Plover. Running it with no args starts a standalone test configuration.
    plugin = EntryPoint(PloverPluginApplication, desc="run the GUI application in Plover plugin mode.")


def main():
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
        return
    if len(matches) > 1:
        print(f'Multiple matches for operation "{mode}". Use more characters.')
        return
    # Reassign the remaining arguments to sys.argv and run the entry point.
    sys.argv = [script, *cmd_opts]
    matches[0]()


if __name__ == '__main__':
    main()
