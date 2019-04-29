""" Main module and entry point for Spectra's Plover plugin application. """

import sys

from spectra_lexer import gui_qt, plover
from spectra_lexer.gui_qt import GUIQtApplication
from spectra_lexer.types import dummy


class PloverPluginApplication(GUIQtApplication):
    """ Master component for the Plover plugin; runs on the standard Qt GUI with a couple (important) differences.
        Notably, the plugin must not create its own QApplication or run its own event loop (unless in test mode). """

    DESCRIPTION = "Run the GUI application in Plover plugin mode."
    CLASS_PATHS = [gui_qt, plover]

    # Class constants required by Plover for toolbar.
    __doc__ = 'See the breakdown of words using steno rules.'
    TITLE = 'Spectra'
    ICON = ':/spectra_lexer/icon.svg'
    ROLE = 'spectra_dialog'
    SHORTCUT = 'Ctrl+L'

    def __init__(self):
        """ This component appears as a dialog to interface with Plover in proxy.
            It must translate some attributes into engine call methods and fake others. """
        super().__init__()
        self.show = lambda *args: self.call("gui_window_show")
        self.close = lambda *args: self.call("gui_window_close")
        # We get our translations from the Plover engine, so auto-loading of translations from disk must be suppressed.
        sys.argv.append("--translations-files=")

    def __getattr__(self, attr):
        """ As a proxy, we fake any attribute we don't want to handle to avoid incompatibility. """
        return dummy

    def event_loop(self, plover_engine=None):
        """ Plover is already running a Qt event loop. Connect the engine and return this proxy to Plover. """
        if plover_engine is None:
            # If Plover is not running, make a fake engine and run some tests with our own event loop.
            self.call("plover_test")
            super().event_loop()
        else:
            self.call("plover_connect", plover_engine)
        return self
