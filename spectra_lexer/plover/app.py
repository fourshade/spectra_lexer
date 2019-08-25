""" Main entry point for Spectra's Plover plugin application. """

from typing import Dict, Sequence

from .interface import PloverInterface
from .types import dummy, PloverCompatibilityTester, PloverEngine
from spectra_lexer.gui_qt import MainWindow, QtApplication


class PloverPluginApplication(QtApplication):
    """ Main entry point and dialog proxy to Plover. Translates some attributes into engine calls and fakes others.
        It runs on the standard Qt GUI with a couple (important) differences.
        Notably, the app must not create its own QApplication object or run its own event loop.
        The Plover engine must be the first argument to the constructor, however it is called. """

    # Class constants required by Plover for toolbar.
    __doc__ = 'See the breakdown of words using steno rules.'
    TITLE = 'Spectra'
    ICON = ':'.join(['asset', *MainWindow.ICON_PATH])
    ROLE = 'spectra_dialog'
    SHORTCUT = 'Ctrl+L'

    VERSION_REQUIRED = "4.0.0.dev8"  # Minimum version of Plover required for plugin compatibility.
    VERSION_TEST = PloverCompatibilityTester(VERSION_REQUIRED)

    engine: PloverEngine
    interface: PloverInterface

    def __init__(self, engine:PloverEngine=None):
        self.engine = engine
        super().__init__()

    def load(self) -> None:
        self.interface = PloverInterface(self._on_new_dictionaries, self._on_new_translation)
        self["plover_engine"] = self.engine
        self["plover_interface"] = self.interface
        super().load()

    def load_translations(self) -> None:
        """ We get our translations from the Plover engine, so auto-loading from disk must be suppressed. """

    def _on_new_dictionaries(self, converted_dict:Dict[str, str]) -> None:
        """ Send any converted translations dictionaries to the main engine. """
        self.steno.RSTranslationsReady(converted_dict)
        self.status("Loaded new dictionaries from Plover engine.")

    def _on_new_translation(self, translation:Sequence[str]) -> None:
        """ User strokes may involve all sorts of custom briefs, so do not attempt to match every key. """
        self.window.update(translation=" -> ".join(translation))
        self.window.action("Query", match_all_keys=False)

    def run(self) -> int:
        """ Connect the engine if the version is compatible and return control to Plover. """
        if self.VERSION_TEST(self.status):
            self.interface.connect(self.engine)
        return 0

    def show(self, *args) -> None:
        self.window.show()

    def close(self, *args) -> None:
        """ Closing the main window should kill the program in standalone mode, but not as a plugin. """
        self.window.close()

    def __getattr__(self, *args):
        """ As a proxy, we fake any attribute we don't want to handle to avoid incompatibility. """
        return dummy


class PloverPluginTest(PloverPluginApplication):

    def run(self) -> int:
        """ Run some simple tests, then run the normal event loop. """
        self.interface.test()
        return self.loop()
