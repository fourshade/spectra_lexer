""" Module for the Plover plugin components of Spectra. """

from functools import partial
import pkg_resources
from typing import Any, Callable, Dict, Iterable, Optional, Sequence, Tuple

from spectra_lexer.app import StenoApplication

from .gui import QtGUI, QtGUIFactory
from .main import QtAppFactory


class dummy:
    """ A robust dummy object. Returns itself through any chain of attribute lookups, subscriptions, and calls. """

    def return_self(self, *_, **__) -> 'dummy':
        return self

    __getattr__ = __getitem__ = __call__ = return_self


# Minimum type interfaces for compatibility with Plover.

class IPloverAction:
    prev_attach: bool
    text: Optional[str]


class IPloverTranslation:
    rtfcre: Tuple[str, ...]
    english: Optional[str]


class IPloverTranslatorState:
    translations: Sequence[IPloverTranslation]


class IPloverStenoDict:
    items: Callable[[], Iterable[Tuple[tuple, dict]]]
    enabled: bool


class IPloverStenoDictCollection:
    dicts: Iterable[IPloverStenoDict]


class IPloverEngine:
    dictionaries: IPloverStenoDictCollection
    translator_state: IPloverTranslatorState
    signal_connect: Callable[[str, Callable], None]
    __enter__ = __exit__ = dummy()


class PloverEngineWrapper:
    """ Connects signals and transfers data from the Plover engine in a thread-safe manner. """

    def __init__(self, engine:IPloverEngine=IPloverEngine()) -> None:
        self._engine = engine  # Engine object, either from Plover or a fake for testing.

    def signal_connect(self, key:str, callback:Callable) -> None:
        """ Connect a Plover engine signal to a callback.
            The callback must be wrapped in a partial for signals to reach it...no idea why. """
        self._engine.signal_connect(key, partial(callback))

    def compile_raw_dict(self, steno_dc:IPloverStenoDictCollection=None) -> Dict[tuple, str]:
        """ Plover dictionaries are not proper Python dicts and cannot be handled as such.
            They only have a subset of the normal dict methods. The fastest of these is .items().
            As a plugin, we lock the Plover engine just long enough to copy these with dict().
            The contents are strings and tuples of strings, so we are thread-safe after this point. """
        # With no args, convert the current set of dictionaries from the engine.
        if steno_dc is None:
            steno_dc = self._engine.dictionaries
        d = {}
        with self._engine:
            for steno_d in steno_dc.dicts:
                if steno_d and steno_d.enabled:
                    d.update(steno_d.items())
        return d

    def get_last_strokes(self) -> Sequence[str]:
        """ Lock the Plover engine thread to access the Plover translator state and get the newest strokes. """
        with self._engine:
            t_list = self._engine.translator_state.translations
            if t_list:
                return list(filter(None, t_list[-1].rtfcre))
            return []


class PloverTranslationParser:
    """ Parses dictionaries and translations from Plover. """

    def __init__(self, sep="/") -> None:
        self._strokes = []     # Current set of contiguous strokes.
        self._text = ""        # Corresponding output text.
        self._join = sep.join  # Join function for Plover stroke strings.

    def convert_dict(self, d:Dict[tuple, str]) -> Dict[str, str]:
        """ Strokes in tuple form must be joined into strings. """
        return dict(zip(map(self._join, d), d.values()))

    def parse_translation(self, strokes:Sequence[str], actions:Sequence[IPloverAction]) -> Optional[Tuple[str, str]]:
        """ Process a Plover translation into standard data types and return the current state if it is valid.
            Make sure that we have at least one new action and strokes from one new valid translation. """
        if not strokes:
            self._reset()
            return None
        # The strokes must have produced English text with at least one alphanumeric character.
        text = "".join([a.text for a in actions if a.text])
        if not any(map(str.isalnum, text)):
            self._reset()
            return None
        # Use the current state if the new text attaches to it, otherwise start fresh.
        if not any([a.prev_attach for a in actions]):
            self._reset()
        # Add all new strokes and text into the current state and return the joined product.
        self._strokes += strokes
        self._text += text
        return self._join(self._strokes), self._text

    def _reset(self) -> None:
        """ Reset the translator state to blank strokes and text. """
        self._strokes = []
        self._text = ""


class PloverExtension:
    """ Main application object for the Plover plugin app configuration. """

    def __init__(self, app:StenoApplication, gui:QtGUI,
                 engine:PloverEngineWrapper, parser:PloverTranslationParser) -> None:
        self._app = app        # Main application object.
        self._gui = gui        # Qt GUI controller.
        self._engine = engine  # Wrapped Plover engine object.
        self._parser = parser  # Converts Plover dictionaries and translates user strokes.

    def connect(self, min_version:str=None) -> None:
        """ Connect the Plover engine if compatible. If the compatibility check fails, send an error message. """
        try:
            if min_version is not None:
                pkg_resources.working_set.require(f"plover>={min_version}")
            self._engine.signal_connect("dictionaries_loaded", self._on_new_dictionaries)
            self._engine.signal_connect("translated", self._on_new_translation)
            self._on_new_dictionaries()
        except pkg_resources.ResolutionError:
            self._gui.set_status(f"ERROR: Plover v{min_version} or greater required.")

    def _on_new_dictionaries(self, steno_dc:IPloverStenoDictCollection=None) -> None:
        """ Convert any translations dictionaries and send them to the main engine. """
        d_raw = self._engine.compile_raw_dict(steno_dc)
        d_converted = self._parser.convert_dict(d_raw)
        self._app.set_translations(d_converted)
        self._gui.set_status("Loaded new dictionaries from Plover engine.")

    def _on_new_translation(self, _, new_actions:Sequence[IPloverAction]) -> None:
        """ Parse user translations into custom queries.
            User strokes may involve all sorts of custom briefs, so do not attempt to match every key. """
        strokes = self._engine.get_last_strokes()
        translation = self._parser.parse_translation(strokes, new_actions)
        if translation is not None:
            state = dict(translation=translation, match_all_keys=False)
            changed = self._app.process_action(state, "Query")
            self._gui.set_state(translation=translation, **changed)


class PloverPlugin(QtAppFactory):
    """ Entry point wrapper and dialog proxy to Plover. Translates some attributes into GUI calls and fakes others.
        In order to be recognized as a valid plugin, this proxy class must face outwards as the entry point itself.
        We must not create our own QApplication object or run our own event loop if Plover is running. """

    VERSION_REQUIRED = "4.0.0.dev8"  # Minimum version of Plover required for plugin compatibility.

    # Class constants required by Plover for toolbar.
    __doc__ = 'See the breakdown of words using steno rules.'
    TITLE = 'Spectra'
    ICON = ':'.join(['asset', *QtGUIFactory.ICON_PATH])
    ROLE = 'spectra_dialog'
    SHORTCUT = 'Ctrl+L'

    def __init__(self, engine:IPloverEngine) -> None:
        """ Main entry point for Spectra's Plover plugin.
            The Plover engine is our only argument. Command-line arguments are not used (sys.argv belongs to Plover).
            We create the main application object, but do not directly expose it. This proxy is returned instead. """
        super().__init__()
        self._engine = engine
        self.build()

    def build_app(self, with_translations=..., **kwargs) -> StenoApplication:
        """ We get translations from the Plover engine, so auto-loading from disk must be suppressed. """
        return super().build_app(with_translations=False, **kwargs)

    def connect(self, app:StenoApplication) -> None:
        """ Connect the Plover engine if it is compatible. This must happen *before* the index check. """
        engine_wrapper = PloverEngineWrapper(self._engine)
        parser = PloverTranslationParser()
        ext = PloverExtension(app, self._gui, engine_wrapper, parser)
        ext.connect(self.VERSION_REQUIRED)
        super().connect(app)

    def __getattr__(self, name:str) -> Any:
        """ As a proxy, we delegate or fake any attribute we don't want to handle to avoid incompatibility. """
        try:
            return getattr(self._gui, name)
        except AttributeError:
            return dummy()
