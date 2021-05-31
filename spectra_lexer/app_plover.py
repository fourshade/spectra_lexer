""" Main module for the Qt GUI plugin for Plover. """

from spectra_lexer import Spectra
from spectra_lexer.app_qt import build_app
from spectra_lexer.plover.plugin import EngineWrapper, IPlover, PloverExtension
from spectra_lexer.qt import ICON_PACKAGE, ICON_PATH


class _Dummy:
    """ A robust dummy object. Returns itself through any chain of attribute lookups, subscriptions, and calls. """

    def return_self(self, *_, **__) -> '_Dummy':
        return self

    __getattr__ = __getitem__ = __call__ = return_self


class PloverPlugin:
    """ Entry point wrapper and dialog proxy to Plover. Translates some attributes into GUI calls and fakes others.
        In order to be recognized as a valid plugin, this proxy class must face outwards as the entry point itself.
        We must not create our own QApplication object or run our own event loop if Plover is running. """

    # Class constants required by Plover for toolbar.
    __doc__ = 'See the breakdown of words using steno rules.'
    TITLE = 'Spectra'
    ICON = ':'.join(['asset', ICON_PACKAGE, ICON_PATH])
    ROLE = 'spectra_dialog'
    SHORTCUT = 'Ctrl+L'

    STROKE_LIMIT = 6  # Maximum strokes to keep in buffer (just so the lexer doesn't shit itself).

    def __init__(self, plover_engine:IPlover.Engine) -> None:
        """ Main entry point for Spectra's Plover plugin. The Plover engine is our only argument.
            Command-line arguments are not used (sys.argv belongs to Plover), and translations are not read from files.
            We must create the main application object *and* start it before __init__ returns.
            The extension is added as attribute 'plover' solely to make it visible to the debug tools. """
        spectra = Spectra(parse_args=False)
        spectra.translations_paths = ()
        self._app = app = build_app(spectra)
        self._ext = app.plover = PloverExtension(EngineWrapper(plover_engine), stroke_limit=self.STROKE_LIMIT)
        app.async_run(self._start)
        app.start()

    def _load_translations(self, steno_dc:IPlover.StenoDictionaryCollection) -> None:
        """ Plover dictionaries may be resent with a signal if they change. """
        translations = self._ext.parse_dictionaries(steno_dc)
        self._app.set_translations(translations)

    def _on_dictionaries_loaded(self, steno_dc:IPlover.StenoDictionaryCollection) -> None:
        """ Load translation dictionaries in async mode to keep the GUI responsive. """
        self._app.async_start("Loading dictionaries...")
        self._app.async_run(self._load_translations, steno_dc)
        self._app.async_finish("Loaded new dictionaries from Plover.")

    def _on_translated(self, *args:IPlover.ActionSequence) -> None:
        """ Look up a user's strokes as they are entered, but *not* while the main search window is active.
            User strokes may involve all sorts of custom briefs, so do not attempt to match every key. """
        translation = self._ext.parse_actions(*args)
        if translation is not None and not self._app.has_focus():
            keys, letters = translation
            self._app.set_options(lexer_strict_mode=False)
            self._app.run_query(keys, letters)

    def _connect(self) -> None:
        """ Connect the Plover engine signals. Must be done on the main thread. """
        self._ext.call_on_dictionaries_loaded(self._on_dictionaries_loaded)
        self._ext.call_on_translated(self._on_translated)

    def _start(self) -> None:
        """ Load translations from the current dictionaries and connect the Plover engine signals if compatible.
            The translations *must* load before the first-run index prompt appears. """
        IPlover.check_compatible()
        translations = self._ext.parse_engine_dictionaries()
        self._app.set_translations(translations)
        self._app.async_queue(self._connect)

    # Interface methods for Plover as a GUI dialog.

    def show(self) -> None:
        self._app.show()

    def showNormal(self) -> None:
        self._app.show()

    def close(self) -> None:
        self._app.close()

    def __getattr__(self, name:str) -> _Dummy:
        """ As a proxy, we fake any attribute we can't find to avoid incompatibility. """
        return _Dummy()
