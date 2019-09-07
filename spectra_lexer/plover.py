""" Module for the Plover plugin components of Spectra. """

from functools import partial
import pkg_resources
from typing import Any, Callable, Dict, Iterable, Optional, Sequence, Tuple

from spectra_lexer.gui_qt import QtGUI, QtMain, QtWindow


class dummy:
    """ A robust dummy object. Returns itself through any chain of attribute lookups, subscriptions, and calls. """

    def ret_self(self, *args, **kwargs):
        return self

    __getattr__ = __getitem__ = __call__ = ret_self


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

    @classmethod
    def test(cls, d:dict=None, *, split_count:int=1):
        """ Make a fake Plover engine for dict conversion testing. """
        if d is None:
            d = {"TEFT": "test", "TE*S": "test", "TEFGT": "testing"}
        self = cls()
        fd = self.dictionaries = IPloverStenoDictCollection()
        fd.dicts = []
        d_list = list(d.items())
        split_list = [dict(d_list[i::split_count]) for i in range(split_count)]
        for split_d in split_list:
            tuple_d = dict(zip(map(tuple, [k.split("/") for k in split_d]), split_d.values()))
            sd = IPloverStenoDict()
            sd.items = tuple_d.items
            sd.enabled = True
            fd.dicts.append(sd)
        return self


class PloverTranslationParser:
    """ Parses dictionaries and translations from Plover. """

    def __init__(self, engine:IPloverEngine) -> None:
        self._engine = engine          # Engine object, either from Plover or a fake for testing.
        self._translation = "", ""     # Current set of contiguous strokes and text.
        self._join_strokes = "/".join  # Join function for Plover stroke strings.

    def signal_connect(self, key, callback):
        """ Connect a Plover engine signal to a callback.
            The callback must be wrapped in a partial for signals to reach it...no idea why. """
        self._engine.signal_connect(key, partial(callback))

    def convert_dicts(self, steno_dc:IPloverStenoDictCollection=None) -> Dict[str, str]:
        """ Plover dictionaries are not proper Python dicts and cannot be handled as such.
            They only have a subset of the normal dict methods. The fastest of these is .items().
            As a plugin, we lock the Plover engine just long enough to copy these with dict().
            The contents are strings and tuples of strings, so we are thread-safe after this point. """
        if steno_dc is None:
            # With no args, convert the current set of dictionaries from the engine.
            steno_dc = self._engine.dictionaries
        with self._engine:
            dicts = [dict(d.items()) for d in steno_dc.dicts if d and d.enabled]
        # Strokes in tuple form must be joined into strings.
        converted_dict = {}
        for d in dicts:
            converted_dict.update(zip(map(self._join_strokes, d), d.values()))
        return converted_dict

    def parse_translation(self, _, new_actions:Sequence[IPloverAction]) -> Optional[Tuple[str, str]]:
        """ Process a Plover translation into standard data types and return the current state if it is valid.
            Make sure that we have at least one new action and strokes from one new valid translation. """
        strokes = self._get_last_strokes()
        if not strokes:
            self._reset()
            return None
        # The strokes must have produced English text with at least one alphanumeric character.
        text = "".join([a.text for a in new_actions if a.text])
        if not any(map(str.isalnum, text)):
            self._reset()
            return None
        # Use the current state if the new text attaches to it, otherwise start fresh.
        if not any([a.prev_attach for a in new_actions]):
            self._reset()
        self._combine(strokes, text)
        return self._translation

    def _get_last_strokes(self) -> Sequence[str]:
        """ Lock the Plover engine thread to access the Plover translator state and get the newest strokes. """
        engine = self._engine
        with engine:
            t_list = engine.translator_state.translations
            if t_list:
                return tuple(t_list[-1].rtfcre)
            return ()

    def _reset(self) -> None:
        """ Reset the translator state to blank strokes and text. """
        self._translation = "", ""

    def _combine(self, new_strokes:Sequence[str], new_text:str) -> None:
        """ Combine all new strokes and text into the current state. """
        strokes, text = self._translation
        new_strokes = filter(None, [strokes, *new_strokes])
        self._translation = self._join_strokes(new_strokes), text + new_text


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
