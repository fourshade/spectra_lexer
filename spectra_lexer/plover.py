""" Main module for the Plover plugin application and its components. """

from functools import partial
import pkg_resources
from typing import Callable, Dict, Iterable, Optional, Sequence, Tuple

from spectra_lexer.resource import RTFCREDict


class IPlover:
    """ Data types and interfaces containing only what is necessary for compatibility with Plover. """

    Strokes = Tuple[str, ...]

    class Action:
        prev_attach: bool
        text: Optional[str]

    ActionSequence = Sequence[Action]

    class Translation:
        rtfcre: "IPlover.Strokes"
        english: Optional[str]

    class TranslatorState:
        translations: Sequence["IPlover.Translation"]

    class StenoDict:
        items: Callable[[], Iterable[Tuple["IPlover.Strokes", str]]]
        enabled: bool

    RawStenoDict = Dict[tuple, str]

    class StenoDictCollection:
        dicts: Iterable["IPlover.StenoDict"]

    class Engine:
        dictionaries: "IPlover.StenoDictCollection"
        translator_state: "IPlover.TranslatorState"
        signal_connect: Callable[[str, Callable], None]
        __enter__: Callable[[], None]
        __exit__: Callable[..., bool]


class EngineWrapper:
    """ Connects signals and transfers data from the Plover engine in a thread-safe manner. """

    def __init__(self, engine:IPlover.Engine) -> None:
        self._engine = engine  # Engine object, either from Plover or a fake for testing.

    def signal_connect(self, key:str, callback:Callable) -> None:
        """ Connect a Plover engine signal to a callback.
            The callback must be wrapped in a partial for signals to reach it...no idea why. """
        self._engine.signal_connect(key, partial(callback))

    def get_dictionaries(self) -> IPlover.StenoDictCollection:
        """ Return the currently loaded set of dictionaries from the engine. """
        return self._engine.dictionaries

    def compile_raw_dict(self, steno_dc:IPlover.StenoDictCollection) -> IPlover.RawStenoDict:
        """ Plover dictionaries are not proper Python dicts and cannot be handled as such.
            They only have a subset of the normal dict methods. The fastest of these is .items().
            As a plugin, we lock the Plover engine just long enough to copy these with dict.update().
            The contents are strings and tuples of strings, so we are thread-safe after this point. """
        d = {}
        with self._engine:
            for steno_d in steno_dc.dicts:
                if steno_d and steno_d.enabled:
                    d.update(steno_d.items())
        return d

    def get_last_strokes(self) -> IPlover.Strokes:
        """ Lock the Plover engine thread to access the Plover translator state and get the newest strokes. """
        with self._engine:
            t_list = self._engine.translator_state.translations
            if t_list:
                strokes = tuple(filter(None, t_list[-1].rtfcre))
            else:
                strokes = ()
        return strokes


class TranslationState:
    """ Translation state from Plover. """

    def __init__(self) -> None:
        self._strokes = []  # Current list of valid, contiguous strokes.
        self._text = ""     # Corresponding output text.

    def strokes(self) -> IPlover.Strokes:
        return tuple(self._strokes)

    def text(self) -> str:
        return self._text

    def __bool__(self) -> bool:
        return bool(self._strokes and self._text)

    def add(self, strokes:IPlover.Strokes, actions:IPlover.ActionSequence) -> None:
        """ Process a Plover translation into standard data types and add it to the current state if it is valid.
            Make sure that we have at least one new action and strokes from one new valid translation.
            If something is invalid, reset the entire state. """
        if not strokes:
            self._reset()
            return
        # The strokes must have produced English text with at least one alphanumeric character.
        text = "".join([a.text for a in actions if a.text])
        if not any(map(str.isalnum, text)):
            self._reset()
            return
        # Use the current state if the new text attaches to it, otherwise start fresh.
        for a in actions:
            if not a.prev_attach:
                self._reset()
                break
        # Add all new strokes and text into the current state and return the joined product.
        self._strokes += strokes
        self._text += text

    def _reset(self) -> None:
        """ Reset the translator state to blank strokes and text. """
        self._strokes = []
        self._text = ""


class PloverExtension:

    VERSION_REQUIRED = "4.0.0.dev8"  # Minimum version of Plover required for plugin compatibility.

    _steno_dc = None           # Current set of dictionaries from the engine.
    _on_new_dictionary = None  # Callback to send new translations dictionaries.
    _on_translation = None     # Callback to send valid user translations.

    def __init__(self, engine:EngineWrapper, state:TranslationState, sep:str) -> None:
        self._engine = engine  # Wrapped Plover engine object.
        self._state = state    # Converts Plover dictionary items and translates user strokes.
        self._join = sep.join  # Join function for Plover stroke strings.

    def get_translations(self) -> RTFCREDict:
        """ Get the current set of dictionaries from the engine. """
        self._steno_dc = self._engine.get_dictionaries()
        return self._convert_dictionaries()

    def call_on_new_dictionary(self, callback:Callable[[RTFCREDict], None]) -> None:
        """ Set a callback to receive dictionaries when Plover loads them (happens on startup, reordering, etc.) """
        self._on_new_dictionary = callback
        self._engine.signal_connect("dictionaries_loaded", self._dictionaries_loaded)

    def call_on_translation(self, callback:Callable[[str, str], None]) -> None:
        """ Set a callback to receive valid translations resulting from user input. """
        self._on_translation = callback
        self._engine.signal_connect("translated", self._translated)

    def _dictionaries_loaded(self, steno_dc:IPlover.StenoDictCollection) -> None:
        """ Convert and merge any new dictionaries into an RTFCREDict and call back with it. """
        if steno_dc is not self._steno_dc:
            self._steno_dc = steno_dc
            d = self._convert_dictionaries()
            self._on_new_dictionary(d)

    def _translated(self, _, new_actions:IPlover.ActionSequence) -> None:
        """ Parse user actions and call back with any valid translations. """
        self._add_actions(new_actions)
        if self._state:
            keys = self._join(self._state.strokes())
            letters = self._state.text()
            self._on_translation(keys, letters)

    def _convert_dictionaries(self) -> RTFCREDict:
        """ Return the current Plover translations joined into strings and converted into an RTFCREDict. """
        d_raw = self._engine.compile_raw_dict(self._steno_dc)
        items_iter = zip(map(self._join, d_raw), d_raw.values())
        return RTFCREDict(items_iter)

    def _add_actions(self, actions:IPlover.ActionSequence) -> None:
        """ Add Plover user actions to the current translation state with the latest strokes. """
        strokes = self._engine.get_last_strokes()
        self._state.add(strokes, actions)

    @classmethod
    def is_compatible(cls) -> bool:
        """ Check the Plover version to see if it is compatible with this extension. """
        try:
            pkg_resources.working_set.require(f"plover>={cls.VERSION_REQUIRED}")
            return True
        except pkg_resources.ResolutionError:
            return False

    @classmethod
    def from_engine(cls, engine:IPlover.Engine, key_sep="/") -> "PloverExtension":
        """ Build a new extension object from a Plover <engine>. """
        wrapper = EngineWrapper(engine)
        state = TranslationState()
        return cls(wrapper, state, key_sep)
