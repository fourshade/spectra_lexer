""" Main entry point for Spectra's Plover plugin application. """

import sys

from .types import PloverEngine
from spectra_lexer import plover
from spectra_lexer.core import Signal
from spectra_lexer.gui_qt.app import GUIQtApplication
from spectra_lexer.gui_qt.window import GUI
from spectra_lexer.types import dummy


class PLOVERApp:

    class Connect:
        @Signal
        def on_engine_connect(self, plover_engine:PloverEngine) -> None:
            """ Connect the Plover engine to ours only if a compatible version of Plover is found. """
            raise NotImplementedError


class PloverPluginApplication(GUIQtApplication, PLOVERApp):
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
        """ Plover is already running a Qt event loop. Create the engine and return this proxy to Plover.
            We get our translations from the Plover engine, so auto-loading from disk must be suppressed. """
        sys.argv.append("--translations-files=NUL.json")
        super().__init__()
        self.show = lambda *args: self.call(GUI.show)
        self.close = lambda *args: self.call(GUI.close)
        self.call(self.Connect, plover_engine)

    def _class_paths(self) -> list:
        main_path, worker_path = paths = super()._class_paths()
        main_path.append(plover)
        return paths

    def __getattr__(self, attr):
        """ As a proxy, we fake any attribute we don't want to handle to avoid incompatibility. """
        return dummy
