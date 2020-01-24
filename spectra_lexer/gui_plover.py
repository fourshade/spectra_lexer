""" Main module for the Qt GUI plugin for Plover. """

from typing import Any

from spectra_lexer.gui_qt import SpectraQt
from spectra_lexer.plover import IncompatibleError, plover_info, PloverExtension


class _Dummy:
    """ A robust dummy object. Returns itself through any chain of attribute lookups, subscriptions, and calls. """

    def return_self(self, *_, **__) -> Any:
        return self

    __getattr__ = __getitem__ = __call__ = return_self


class PloverPlugin:
    """ Entry point wrapper and dialog proxy to Plover. Translates some attributes into GUI calls and fakes others.
        In order to be recognized as a valid plugin, this proxy class must face outwards as the entry point itself.
        We must not create our own QApplication object or run our own event loop if Plover is running. """

    # Class constants required by Plover for toolbar.
    __doc__ = 'See the breakdown of words using steno rules.'
    TITLE = 'Spectra'
    ICON = ':'.join(['asset', *SpectraQt.ICON_PATH])
    ROLE = 'spectra_dialog'
    SHORTCUT = 'Ctrl+L'

    def __init__(self, engine:Any) -> None:
        """ Main entry point for Spectra's Plover plugin. Create the extension and connect it only if compatible.
            The Plover engine is our only argument. Command-line arguments are not used (sys.argv belongs to Plover).
            We create the main application object, but do not directly expose it. This proxy is returned instead. """
        main = SpectraQt()
        self._app = app = main.build_app()
        self._ext = ext = PloverExtension(engine)
        try:
            # Load the app's user files followed by the current Plover dictionaries.
            plover_info.check_compatible()
            main.translations_files = []
            main.load_app_async(app)
            self.on_dictionaries_loaded()
            ext.call_on_dictionaries_loaded(self.on_dictionaries_loaded)
            ext.call_on_translated(self.on_translated)
        except IncompatibleError as e:
            # If the compatibility check fails, abort the loading sequence and show an error message.
            app.set_status(f"ERROR: {e}")

    def _load_translations(self, *args) -> None:
        """ Convert Plover translation dictionaries to string-key format and send the result to the main engine. """
        translations = self._ext.parse_dictionaries(*args)
        self._app.set_translations(translations)

    def on_dictionaries_loaded(self, *args) -> None:
        """ Load translation dictionaries in async mode to keep the GUI responsive. """
        self._app.run_async(self._load_translations, *args, msg_start="Loading dictionaries...",
                            msg_done="Loaded new dictionaries from Plover.")

    def on_translated(self, *args) -> None:
        """ User strokes may involve all sorts of custom briefs, so do not attempt to match every key. """
        translation = self._ext.parse_actions(*args)
        if translation is not None:
            self._app.on_query(translation, lexer_strict_mode=False)

    def __getattr__(self, name:str) -> Any:
        """ As a proxy, we delegate or fake any attribute we don't want to handle to avoid incompatibility. """
        try:
            return getattr(self._app, name)
        except AttributeError:
            return _Dummy()
