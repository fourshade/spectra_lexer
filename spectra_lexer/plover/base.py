from typing import Any

import pkg_resources

from .parser import PloverTranslationParser
from .types import dummy, IPloverEngine
from spectra_lexer.gui_qt import QtGUI, QtMain, QtWindow


class PloverGUI(QtGUI):
    """ Top-level application object for the Plover plugin app configuration. """

    VERSION_REQUIRED = "4.0.0.dev8"  # Minimum version of Plover required for plugin compatibility.

    def __init__(self, *args, parser:PloverTranslationParser) -> None:
        super().__init__(*args)
        self.parser = parser  # Converts Plover dictionaries and translates user strokes.

    def _subcls_tasks(self) -> None:
        """ Connect the Plover engine if it is compatible. This must happen *before* the index check. """
        try:
            pkg_resources.working_set.require(f"plover>={self.VERSION_REQUIRED}")
            self.parser.signal_connect("dictionaries_loaded", self.on_new_dictionaries)
            self.parser.signal_connect("translated", self.on_new_translation)
            self.on_new_dictionaries()
        except pkg_resources.ResolutionError:
            # If the compatibility check fails, send an error message.
            self.window.set_status(f"ERROR: Plover v{self.VERSION_REQUIRED} or greater required.")
        super()._subcls_tasks()

    def on_new_dictionaries(self, *args) -> None:
        """ Convert any translations dictionaries and send them to the main engine. """
        converted_dict = self.parser.convert_dicts(*args)
        self.app.set_translations(converted_dict)
        self.window.set_status("Loaded new dictionaries from Plover engine.")

    def on_new_translation(self, *args) -> None:
        """ Parse user translations into custom queries to be handled by the GUI.
            User strokes may involve all sorts of custom briefs, so do not attempt to match every key. """
        translation = self.parser.parse_translation(*args)
        if translation is not None:
            self.state.query(*translation)


class PloverMain(QtMain):
    """ We get translations from the Plover engine, so auto-loading from disk must be suppressed. """
    translations_files = []


class plover:
    """ Entry point wrapper and dialog proxy to Plover. Translates some attributes into app calls and fakes others.
        In order to be recognized as a valid plugin, this proxy class must face outwards as the entry point itself.
        We must not create our own QApplication object or run our own event loop if Plover is running. """

    # Class constants required by Plover for toolbar.
    __doc__ = 'See the breakdown of words using steno rules.'
    TITLE = 'Spectra'
    ICON = ':'.join(['asset', *QtWindow.ICON_PATH])
    ROLE = 'spectra_dialog'
    SHORTCUT = 'Ctrl+L'

    def __init__(self, engine:IPloverEngine) -> None:
        """ Main entry point for Spectra's Plover plugin.
            The Plover engine is the only argument. Command-line arguments are not used (sys.argv belongs to Plover).
            We create the main application object, but do not directly expose it. This proxy is returned instead. """
        self.original = PloverMain().build_gui(PloverGUI, parser=PloverTranslationParser(engine))

    def __getattr__(self, attr:str) -> Any:
        """ As a proxy, we delegate or fake any attribute we don't want to handle to avoid incompatibility. """
        try:
            return getattr(self.original, attr)
        except AttributeError:
            return dummy()
