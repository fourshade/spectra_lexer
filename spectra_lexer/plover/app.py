""" Main entry point for Spectra's Plover plugin application. """

import sys
from typing import Dict, Tuple

from PyQt5.QtWidgets import QApplication

from .interface import PloverInterface
from .types import dummy, PloverAction, PloverCompatibilityTester, PloverEngine
from spectra_lexer.gui_qt import QtGUI, QtApplication


class PloverPluginApplication(QtApplication):
    """ Main Plover application class. Runs on the standard Qt GUI with a couple (important) differences.
        Notably, the app must not create its own QApplication object or run its own event loop. """

    VERSION_REQUIRED = "4.0.0.dev8"  # Minimum version of Plover required for plugin compatibility.
    VERSION_TEST = PloverCompatibilityTester(VERSION_REQUIRED)

    translation_files = []  # We get translations from the Plover engine, so auto-loading from disk must be suppressed.

    interface: PloverInterface

    def __init__(self, engine:PloverEngine, *argv:str):
        """ The Plover engine must be the first argument to the constructor, however it is called.
            Create the interface and connect the engine to the callbacks if the version is compatible. """
        super().__init__(*argv)
        self.interface = self["plover"] = PloverInterface(engine)
        if self.VERSION_TEST(self.status):
            self.interface.connect(self._on_new_dictionaries, self._on_new_translation)

    def _on_new_dictionaries(self, converted_dict:Dict[str, str]) -> None:
        """ Send any converted translations dictionaries to the main engine. """
        self.steno.RSTranslationsReady(converted_dict)
        self.status("Loaded new dictionaries from Plover engine.")

    def _on_new_translation(self, translation:Tuple[str, str]) -> None:
        """ User strokes may involve all sorts of custom briefs, so do not attempt to match every key. """
        self.gui.update(translation=" -> ".join(translation))
        self.gui.action("Query", match_all_keys=False)


class plover_app:
    """ Main entry point and dialog proxy to Plover. Translates some attributes into app calls and fakes others. """

    # Class constants required by Plover for toolbar.
    __doc__ = 'See the breakdown of words using steno rules.'
    TITLE = 'Spectra'
    ICON = ':'.join(['asset', *QtGUI.ICON_PATH])
    ROLE = 'spectra_dialog'
    SHORTCUT = 'Ctrl+L'

    app: PloverPluginApplication

    def __init__(self, *args):
        """ Create the main application, but do not directly expose it. This object will be returned instead. """
        self.app = PloverPluginApplication(*args)

    def __getattr__(self, attr:str):
        """ As a proxy, we delegate or fake any attribute we don't want to handle to avoid incompatibility. """
        return getattr(self.app, attr, dummy)


def plover_test(*argv:str) -> int:
    """ Entry point for Plover application in standalone mode. Only useful for testing purposes. """
    qt_app = QApplication(sys.argv)
    app = PloverPluginApplication(PloverEngine.test(), *argv)
    app.interface.parse_translation(None, (PloverAction(),))
    return qt_app.exec_()
