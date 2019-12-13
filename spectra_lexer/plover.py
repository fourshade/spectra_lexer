""" Main module for the Plover plugin application and its components. """

from functools import partial
import pkg_resources
from typing import Any, Callable, Dict, Iterable, Optional, Sequence, Tuple

from spectra_lexer.gui_qt import SpectraQtBase
from spectra_lexer.resource import RTFCREDict


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
    items: Callable[[], Iterable[Tuple[tuple, str]]]
    enabled: bool


class IPloverStenoDictCollection:
    dicts: Iterable[IPloverStenoDict]


class IPloverEngine:
    dictionaries: IPloverStenoDictCollection
    translator_state: IPloverTranslatorState
    signal_connect: Callable[[str, Callable], None]
    __enter__: Callable[[], None]
    __exit__: Callable[..., bool]


class PloverEngineWrapper:
    """ Connects signals and transfers data from the Plover engine in a thread-safe manner. """

    def __init__(self, engine:IPloverEngine) -> None:
        self._engine = engine  # Engine object, either from Plover or a fake for testing.

    def signal_connect(self, key:str, callback:Callable) -> None:
        """ Connect a Plover engine signal to a callback.
            The callback must be wrapped in a partial for signals to reach it...no idea why. """
        self._engine.signal_connect(key, partial(callback))

    def compile_raw_dict(self, steno_dc:IPloverStenoDictCollection) -> Dict[tuple, str]:
        """ Plover dictionaries are not proper Python dicts and cannot be handled as such.
            They only have a subset of the normal dict methods. The fastest of these is .items().
            As a plugin, we lock the Plover engine just long enough to copy these with dict().
            The contents are strings and tuples of strings, so we are thread-safe after this point. """
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
                strokes = list(filter(None, t_list[-1].rtfcre))
            else:
                strokes = []
        return strokes


class PloverTranslationParser:
    """ Parses translations from Plover. """

    def __init__(self, sep="/") -> None:
        self._strokes = []     # Current set of contiguous strokes.
        self._text = ""        # Corresponding output text.
        self._join = sep.join  # Join function for Plover stroke strings.

    def convert_dict(self, d:Dict[tuple, str]) -> RTFCREDict:
        """ Strokes in tuple form must be joined into strings. """
        return RTFCREDict(zip(map(self._join, d), d.values()))

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


class dummy:
    """ A robust dummy object. Returns itself through any chain of attribute lookups, subscriptions, and calls. """

    def return_self(self, *_, **__) -> 'dummy':
        return self

    __getattr__ = __getitem__ = __call__ = return_self


class PloverPlugin(SpectraQtBase):
    """ Entry point wrapper and dialog proxy to Plover. Translates some attributes into GUI calls and fakes others.
        In order to be recognized as a valid plugin, this proxy class must face outwards as the entry point itself.
        We must not create our own QApplication object or run our own event loop if Plover is running. """

    VERSION_REQUIRED = "4.0.0.dev8"  # Minimum version of Plover required for plugin compatibility.

    # Class constants required by Plover for toolbar.
    __doc__ = 'See the breakdown of words using steno rules.'
    TITLE = 'Spectra'
    ICON = ':'.join(['asset', *SpectraQtBase.ICON_PATH])
    ROLE = 'spectra_dialog'
    SHORTCUT = 'Ctrl+L'

    def __init__(self, engine:IPloverEngine) -> None:
        """ Main entry point for Spectra's Plover plugin.
            The Plover engine is our only argument. Command-line arguments are not used (sys.argv belongs to Plover).
            We create the main application object, but do not directly expose it. This proxy is returned instead. """
        self._steno_dc = engine.dictionaries        # Current set of dictionaries from the engine.
        self._engine = PloverEngineWrapper(engine)  # Wrapped Plover engine object.
        self._parser = PloverTranslationParser()    # Converts Plover dictionaries and translates user strokes.
        self._app = app = self.build_app()          # Qt GUI app object.
        app.connect_gui()
        app.show()
        if self._is_compatible():
            # Connect the Plover engine to the parsing callbacks if it is compatible.
            self._engine.signal_connect("dictionaries_loaded", self._on_dictionaries_loaded)
            self._engine.signal_connect("translated", self._on_translated)
            self.load_app_async(app)
        else:
            # If the compatibility check fails, abort the loading sequence and show an error message.
            app.set_status(f"ERROR: Plover v{self.VERSION_REQUIRED} or greater required.")

    def _is_compatible(self) -> bool:
        """ Check the Plover version to see if it is compatible. """
        try:
            pkg_resources.working_set.require(f"plover>={self.VERSION_REQUIRED}")
            return True
        except pkg_resources.ResolutionError:
            return False

    def _on_dictionaries_loaded(self, steno_dc:IPloverStenoDictCollection) -> None:
        """ Convert Plover translation dictionaries to string-key format and send the result to the main engine. """
        if steno_dc is not self._steno_dc:
            self._steno_dc = steno_dc
            self._app.run_async(self._load_dictionaries_async, msg_start="Loading dictionaries...",
                                msg_done="Loaded new dictionaries from Plover engine.")

    def _load_dictionaries_async(self) -> None:
        d = self._plover_translations()
        self._app.set_translations(d)

    def _plover_translations(self) -> RTFCREDict:
        """ We get translations from the Plover engine instead of auto-loading from disk. """
        d_raw = self._engine.compile_raw_dict(self._steno_dc)
        return self._parser.convert_dict(d_raw)

    def _on_translated(self, _, new_actions:Sequence[IPloverAction]) -> None:
        """ Parse user translations into custom queries and send signals with valid ones. """
        strokes = self._engine.get_last_strokes()
        translation = self._parser.parse_translation(strokes, new_actions)
        if translation is not None:
            # User strokes may involve all sorts of custom briefs, so do not attempt to match every key.
            self._app.on_query(translation, lexer_strict_mode=False)

    def __getattr__(self, name:str) -> Any:
        """ As a proxy, we delegate or fake any attribute we don't want to handle to avoid incompatibility. """
        try:
            return getattr(self._app, name)
        except AttributeError:
            return dummy()
