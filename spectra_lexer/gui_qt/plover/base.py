from typing import Any

import pkg_resources

from .parser import PloverTranslationParser
from .types import dummy, PloverEngine
from spectra_lexer.app import StenoApplication
from spectra_lexer.gui_qt.window import WindowController


class PloverInterface:
    """ Main Plover extension class. Runs on the standard Qt GUI with a couple (important) differences. """

    VERSION_REQUIRED = "4.0.0.dev8"  # Minimum version of Plover required for plugin compatibility.

    _engine: PloverEngine
    _parser: PloverTranslationParser
    _window: WindowController
    _app: StenoApplication = None

    def __init__(self, window:WindowController, engine:PloverEngine=None) -> None:
        if engine is None:
            engine = PloverEngine.test()
        self._engine = engine
        self._parser = PloverTranslationParser(engine)
        self._window = window

    def connect(self, app:StenoApplication) -> None:
        """ Connect the Plover engine only if the Plover version is compatible. """
        self._app = app
        try:
            pkg_resources.working_set.require(f"plover>={self.VERSION_REQUIRED}")
            self._engine.signal_connect("dictionaries_loaded", self.on_new_dictionaries)
            self._engine.signal_connect("translated", self.on_new_translation)
            self.on_new_dictionaries()
        except pkg_resources.ResolutionError:
            # If the compatibility check fails, send an error message.
            self._window.set_status(f"ERROR: Plover v{self.VERSION_REQUIRED} or greater required.")

    def on_new_dictionaries(self, *args) -> None:
        """ Convert any translations dictionaries and send them to the main engine. """
        converted_dict = self._parser.convert_dicts(*args)
        self._app.set_translations(converted_dict)
        self._window.set_status("Loaded new dictionaries from Plover engine.")

    def on_new_translation(self, *args) -> None:
        """ Parse user translations into custom queries to be handled by the GUI. """
        translation = self._parser.parse_translation(*args)
        if translation is not None:
            self._window.user_query(*translation)


class PloverProxy:
    """ Entry point wrapper and dialog proxy to Plover. Translates some attributes into app calls and fakes others.
        In order to be recognized as a valid plugin, this proxy class must face outwards as the entry point itself. """

    # Class constants required by Plover for toolbar.
    __doc__ = 'See the breakdown of words using steno rules.'
    TITLE = 'Spectra'
    ICON = ':'.join(['asset', *WindowController.ICON_PATH])
    ROLE = 'spectra_dialog'
    SHORTCUT = 'Ctrl+L'

    app: object  # The real application object.

    def __getattr__(self, attr:str) -> Any:
        """ As a proxy, we delegate or fake any attribute we don't want to handle to avoid incompatibility. """
        return getattr(self.app, attr, dummy)
