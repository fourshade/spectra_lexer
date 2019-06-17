""" Main entry point for Spectra's Plover plugin application. """

import sys

from .base import PLOVER
from .types import PloverAction, PloverCompatibilityTester, PloverEngine
from spectra_lexer import plover
from spectra_lexer.gui_qt.app import QtApplication
from spectra_lexer.types import dummy

# Minimum version of Plover required for plugin compatibility.
VERSION_REQUIRED = "4.0.0.dev8"


class _PloverPluginApplication(QtApplication, PLOVER):
    """ Master component for the Plover plugin; runs on the standard Qt GUI with a couple (important) differences. """

    def __init__(self, plover_engine:PloverEngine, compat_check:bool=True):
        """ We get our translations from the Plover engine, so auto-loading from disk must be suppressed. """
        sys.argv.append("--translations-files=NUL.json")
        super().__init__()
        # Add the Plover engine only if a compatible version is found.
        if not compat_check or PloverCompatibilityTester(self.SYSStatus)(VERSION_REQUIRED):
            self.PLOVER_ENGINE = plover_engine

    def _worker_class_paths(self) -> list:
        """ Parsing large dictionaries is expensive, so the Plover plugin components run on the worker thread. """
        return [*super()._worker_class_paths(), plover]

    def run(self) -> None:
        """ Plover engine signals can only be caught by the main thread, so connect them here. """
        engine = self.PLOVER_ENGINE
        engine.signal_connect("dictionaries_loaded", self.FoundDicts)
        engine.signal_connect("translated", self.FoundTranslation)
        # Load the current Plover dictionaries to finish engine setup.
        self.FoundDicts(engine.dictionaries)


class PloverPluginProxy(_PloverPluginApplication):
    """ Main entry point and dialog proxy to Plover. Translates some attributes into engine calls and fakes others.
        In this mode, the application must not create its own QApplication object or run its own event loop. """

    DESCRIPTION = "Run the GUI application in Plover plugin mode. The Plover engine must be the first argument."

    # Class constants required by Plover for toolbar.
    __doc__ = 'See the breakdown of words using steno rules.'
    TITLE = 'Spectra'
    ICON = 'asset:spectra_lexer:gui_qt/widgets/icon.svg'
    ROLE = 'spectra_dialog'
    SHORTCUT = 'Ctrl+L'

    def __init__(self, *args):
        """ Create the app, start it, and return this proxy to Plover. """
        super().__init__(*args)
        self.start()

    def show(self, *args) -> None:
        self.GUIQTShowWindow()

    def close(self, *args) -> None:
        self.GUIQTCloseWindow()

    def __getattr__(self, *args):
        """ As a proxy, we fake any attribute we don't want to handle to avoid incompatibility. """
        return dummy


class PloverPluginTest(_PloverPluginApplication):
    """ Make a fake Plover engine and run some simple tests. """

    DESCRIPTION = "Run the GUI application in Plover plugin test mode."

    def __init__(self):
        """ We do not need Plover for the tests, so compatibility is not required. """
        super().__init__(PloverEngine.test(), compat_check=False)

    def run(self) -> None:
        super().run()
        self.FoundTranslation(None, [PloverAction()])
        QtApplication.run(self)


# Running this app from the command line starts a standalone test configuration.
PloverPluginTest.set_entry_point("plover_test")
