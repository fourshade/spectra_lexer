""" Main entry point for Spectra's Plover plugin application. """

import sys

from spectra_lexer import plover
from spectra_lexer.gui_qt import GUIQtApplication
from spectra_lexer.types import dummy


class PloverPluginApplication(GUIQtApplication):
    """ Master component for the Plover plugin; runs on the standard Qt GUI with a couple (important) differences.
        Notably, the plugin must not create its own QApplication or run its own event loop (unless in test mode).
        It appears as a dialog proxy to Plover, translating some attributes into engine calls and faking others. """

    # Running the app from the command line with no args starts a standalone test configuration.
    DESCRIPTION = "Run the GUI application in Plover plugin test mode."

    # Class constants required by Plover for toolbar.
    __doc__ = 'See the breakdown of words using steno rules.'
    TITLE = 'Spectra'
    ICON = ':/spectra_lexer/icon.svg'
    ROLE = 'spectra_dialog'
    SHORTCUT = 'Ctrl+L'

    def __init__(self, plover_engine=None):
        """ Plover is already running a Qt event loop. Create the engine and return this proxy to Plover. """
        # We get our translations from the Plover engine, so auto-loading of translations from disk must be suppressed.
        sys.argv.append("--translations-files=")
        super().__init__()
        self.show = lambda *args: self.call("gui_window_show")
        self.close = lambda *args: self.call("gui_window_close")
        if plover_engine is None:
            # If Plover is not running, make a fake engine. main() will start the event loop in this case.
            self.call("plover_test")
        else:
            self.call("plover_connect", plover_engine)

    def _class_paths(self) -> list:
        paths = super()._class_paths()
        paths[0].append(plover)
        return paths

    def __getattr__(self, attr):
        """ As a proxy, we fake any attribute we don't want to handle to avoid incompatibility. """
        return dummy
