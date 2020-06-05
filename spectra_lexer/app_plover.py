""" Main module for the Qt GUI plugin for Plover. """

from typing import Any

from spectra_lexer import SpectraOptions
from spectra_lexer.gui_qt import build_app, GUILayerExtended, QtGUIApplication
from spectra_lexer.plover.plugin import EngineWrapper, IPlover, PloverExtension
from spectra_lexer.qt import WINDOW_ICON_PATH


class PloverPluginApplication:
    """ The highest application layer, exclusive to Plover. Probably needs some flattening. """

    def __init__(self, gui:GUILayerExtended, app:QtGUIApplication, ext:PloverExtension) -> None:
        self._gui = gui
        self._app = app
        self._ext = ext

    def _set_translations(self, *args) -> None:
        """ Convert Plover translation dictionaries to string-key format and send the result to the main engine. """
        translations = self._ext.parse_dictionaries(*args)
        self._gui.set_translations(translations)

    def _load_user_files(self) -> None:
        """ Load initial user data. In this case the translations come from the current Plover dictionaries. """
        self._set_translations()
        self._gui.load_start_examples()

    def on_dictionaries_loaded(self, steno_dc:IPlover.StenoDictionaryCollection) -> None:
        """ Load translation dictionaries in async mode to keep the GUI responsive. """
        self._app.run_async(self._set_translations, steno_dc, msg_start="Loading dictionaries...",
                            msg_finish="Loaded new dictionaries from Plover.")

    def on_translated(self, *args:IPlover.ActionSequence) -> None:
        """ Look up a user's strokes as they are entered, but *not* while the main search window is active.
            User strokes may involve all sorts of custom briefs, so do not attempt to match every key. """
        translation = self._ext.parse_actions(*args)
        if translation is not None and not self._app.has_focus():
            keys, letters = translation
            self._app.gui_query(keys, letters, strict=False)

    def start(self) -> None:
        """ Start the main app and connect the Plover extension only if compatible. """
        try:
            IPlover.is_compatible()
            self._app.start(self._load_user_files)
            self._ext.call_on_dictionaries_loaded(self.on_dictionaries_loaded)
            self._ext.call_on_translated(self.on_translated)
        except IPlover.IncompatibleError as e:
            # If the compatibility check fails, abort the loading sequence and show an error message.
            self._app.set_status(f"ERROR: {e}")

    def dialog_proxy(self) -> object:
        """ Return a delegate that will interface with Plover as a GUI dialog. """
        return self._app


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
    ICON = ':'.join(['asset', *WINDOW_ICON_PATH])
    ROLE = 'spectra_dialog'
    SHORTCUT = 'Ctrl+L'

    STROKE_LIMIT = 6  # Maximum strokes to keep in buffer (just so the lexer doesn't shit itself).

    def __init__(self, plover_engine:IPlover.Engine) -> None:
        """ Main entry point for Spectra's Plover plugin. The Plover engine is our only argument.
            Command-line arguments are not used (sys.argv belongs to Plover).
            We create the main application object, but do not expose it except through __getattr__. """
        opts = SpectraOptions()
        spectra = opts.compile(parse_args=False)
        index_path = opts.index_path()
        cfg_path = opts.config_path()
        gui = GUILayerExtended(spectra.translations_io, index_path, cfg_path, spectra.search_engine,
                               spectra.analyzer, spectra.graph_engine, spectra.board_engine)
        app = build_app(gui, spectra.log)
        ext = PloverExtension(EngineWrapper(plover_engine), stroke_limit=self.STROKE_LIMIT)
        # Add the extension as an app attribute so it is visible to the Qt app debug tools.
        app.plover = ext
        self._main = PloverPluginApplication(gui, app, ext)
        self._main.start()

    def __getattr__(self, name:str) -> Any:
        """ As a proxy, we delegate or fake any attribute we don't want to handle to avoid incompatibility. """
        try:
            dialog = self._main.dialog_proxy()
            return getattr(dialog, name)
        except AttributeError:
            return _Dummy()
