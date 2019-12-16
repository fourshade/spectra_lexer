""" Main module for the Qt GUI plugin for Plover. """

from typing import Any

from spectra_lexer.gui_qt import SpectraQt
from spectra_lexer.plover import PloverExtension
from spectra_lexer.resource import RTFCREDict


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
        """ Main entry point for Spectra's Plover plugin.
            The Plover engine is our only argument. Command-line arguments are not used (sys.argv belongs to Plover).
            We create the main application object, but do not directly expose it. This proxy is returned instead. """
        main = SpectraQt()
        self._app = app = main.build_app()
        if PloverExtension.is_compatible():
            # Create the extension with the Plover engine and connect it if it is compatible.
            ext = PloverExtension.from_engine(engine)
            ext.call_on_new_dictionary(self._on_new_dictionary)
            ext.call_on_translation(self._on_translation)
            # FIXME - This is a terrible method monkey patch.
            main._plover_translations = ext.get_translations
            main.load_app_async(app)
        else:
            # If the compatibility check fails, abort the loading sequence and show an error message.
            app.set_enabled(False)
            app.set_status(f"ERROR: Plover v{PloverExtension.VERSION_REQUIRED} or greater required.")

    def _on_new_dictionary(self, translations:RTFCREDict) -> None:
        """ Convert Plover translation dictionaries to string-key format and send the result to the main engine. """
        self._app.run_async(self._app.set_translations, translations, msg_start="Loading dictionaries...",
                            msg_done="Loaded new dictionaries from Plover engine.")

    def _on_translation(self, keys:str, letters:str) -> None:
        """ User strokes may involve all sorts of custom briefs, so do not attempt to match every key. """
        self._app.on_query((keys, letters), lexer_strict_mode=False)

    def __getattr__(self, name:str) -> Any:
        """ As a proxy, we delegate or fake any attribute we don't want to handle to avoid incompatibility. """
        try:
            return getattr(self._app, name)
        except AttributeError:
            return _Dummy()
