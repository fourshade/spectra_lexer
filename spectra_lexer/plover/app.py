""" Main entry point for Spectra's Plover plugin application. """

import sys

from .base import PLOVER
from .types import PloverAction, PloverCompatibilityTester, PloverEngine
from spectra_lexer import plover
from spectra_lexer.gui_qt.app import QtApplication
from spectra_lexer.types import dummy

# Minimum version of Plover required for plugin compatibility.
VERSION_REQUIRED = "4.0.0.dev8"


class PloverPluginApplication(QtApplication, PLOVER):
    """ Main entry point and dialog proxy to Plover. Translates some attributes into engine calls and fakes others.
        It runs on the standard Qt GUI with a couple (important) differences.
        Notably, the app must not create its own QApplication object or run its own event loop.
        The Plover engine must be the first argument to the constructor, however it is called. """

    # Class constants required by Plover for toolbar.
    __doc__ = 'See the breakdown of words using steno rules.'
    TITLE = 'Spectra'
    ICON = 'asset:spectra_lexer:gui_qt/widgets/icon.svg'
    ROLE = 'spectra_dialog'
    SHORTCUT = 'Ctrl+L'

    _plover: PloverEngine

    def __init__(self, plover_engine:PloverEngine):
        """ We get our translations from the Plover engine, so auto-loading from disk must be suppressed. """
        sys.argv.append("--translations-files=NUL.json")
        self._plover = plover_engine
        super().__init__()

    def _worker_class_paths(self) -> list:
        """ Parsing large dictionaries is expensive, so the Plover plugin components run on the worker thread. """
        return [*super()._worker_class_paths(), plover]

    def run(self) -> None:
        """ Plover engine signals can only be caught by the main thread, so connect them here. """
        if self.compat_check():
            engine = self.PLOVER_ENGINE = self._plover
            engine.signal_connect("dictionaries_loaded", self.FoundDicts)
            engine.signal_connect("translated", self.FoundTranslation)
            # Load the current Plover dictionaries to finish engine setup.
            self.FoundDicts(engine.dictionaries)

    def compat_check(self) -> bool:
        """ Add the Plover engine only if the version is compatible. """
        return PloverCompatibilityTester(self.SYSStatus)(VERSION_REQUIRED)

    def show(self, *args) -> None:
        self.GUIQTShowWindow()

    def close(self, *args) -> None:
        self.GUIQTCloseWindow()

    def __getattr__(self, *args):
        """ As a proxy, we fake any attribute we don't want to handle to avoid incompatibility. """
        return dummy


class PloverPluginTest(PloverPluginApplication):
    """ Make a fake Plover engine and run some simple tests. """

    def __init__(self, *args):
        super().__init__(PloverEngine.test())

    def compat_check(self) -> bool:
        """ We do not need Plover for the tests, so compatibility is not required. """
        return True

    def run(self) -> None:
        super().run()
        self.FoundTranslation(None, [PloverAction()])
        QtApplication.run(self)
