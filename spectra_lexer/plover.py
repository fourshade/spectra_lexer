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

    class StenoDictCollection:
        dicts: Iterable["IPlover.StenoDict"]

    class Engine:
        dictionaries: "IPlover.StenoDictCollection"
        translator_state: "IPlover.TranslatorState"
        signal_connect: Callable[[str, Callable], None]
        __enter__: Callable[[], None]
        __exit__: Callable[..., bool]


class RawStenoDict(Dict[IPlover.Strokes, str]):
    """ Dict of tuple-keyed Plover translations. """

    @classmethod
    def from_steno_dc(cls, steno_dc:IPlover.StenoDictCollection) -> "RawStenoDict":
        """ Plover dictionaries are not proper Python dicts and cannot be handled as such.
            They only have a subset of the normal dict methods. The fastest of these is .items(). """
        self = cls()
        for steno_d in steno_dc.dicts:
            if steno_d and steno_d.enabled:
                self.update(steno_d.items())
        return self

    def to_string_dict(self, stroke_delim:str) -> RTFCREDict:
        """ Convert this dict to use string keys. """
        keys_iter = map(stroke_delim.join, self)
        items_iter = zip(keys_iter, self.values())
        return RTFCREDict(items_iter)


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

    def compile_raw_dict(self, steno_dc:IPlover.StenoDictCollection) -> RawStenoDict:
        """ As a plugin, we lock the Plover engine just long enough to copy its steno dictionaries.
            The contents are strings and tuples of strings, so we are thread-safe after this point. """
        with self._engine:
            return RawStenoDict.from_steno_dc(steno_dc)

    def get_last_strokes(self) -> Sequence[str]:
        """ Lock the Plover engine thread to access the Plover translator state and get the newest strokes. """
        with self._engine:
            tr_list = self._engine.translator_state.translations
            new_strokes = tr_list[-1].rtfcre if tr_list else ()
            return [s for s in new_strokes if s]


class TranslationState:
    """ Translation state from Plover user strokes. """

    def __init__(self, strokes:Sequence[str]=(), actions:IPlover.ActionSequence=()) -> None:
        self._strokes = strokes  # Sequence of contiguous strokes.
        self._actions = actions  # Sequence of corresponding Plover actions.

    def is_valid(self) -> bool:
        """ Return True if the translation state is valid for parsing into a query.
            The strokes must have produced English text with at least one alphanumeric character. """
        if not self._strokes:
            return False
        for a in self._actions:
            if a.text:
                for char in a.text:
                    if char.isalnum():
                        return True
        return False

    def is_attachment(self) -> bool:
        """ Return True if this text attaches to the previous text. """
        for a in self._actions:
            if not a.prev_attach:
                return False
        return True

    def __add__(self, other:"TranslationState") -> "TranslationState":
        """ Add two translation states together. """
        strokes = [*self._strokes, *other._strokes]
        actions = [*self._actions, *other._actions]
        return self.__class__(strokes, actions)

    def __and__(self, other:"TranslationState") -> "TranslationState":
        """ Merge two translation states that occur together. """
        # If the new translation is invalid, keep only this state.
        if not other.is_valid():
            return self
        # If the new translation is independent, keep only that one.
        if not other.is_attachment():
            return other
        # If the new translation attaches, add all strokes and actions to make a new state.
        return self + other

    def to_strings(self, stroke_delim:str) -> Tuple[str, str]:
        """ Return the string values of this translation state. """
        keys = stroke_delim.join(self._strokes)
        letters = "".join([a.text for a in self._actions if a.text])
        return keys, letters


class PloverExtension:

    _steno_dc = None           # Current set of dictionaries from the engine.
    _on_new_dictionary = None  # Callback to send new translations dictionaries.
    _on_translation = None     # Callback to send valid user translations.

    def __init__(self, engine:EngineWrapper, stroke_delim:str) -> None:
        self._engine = engine              # Wrapped Plover engine object.
        self._stroke_delim = stroke_delim  # Delimiter for Plover stroke strings.
        self._state = TranslationState()   # Contains current user strokes and actions.

    def refresh_dictionaries(self) -> None:
        """ Load the current set of dictionaries from the engine. """
        steno_dc = self._engine.get_dictionaries()
        self._dictionaries_loaded(steno_dc)

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
            d_raw = self._engine.compile_raw_dict(steno_dc)
            translations = d_raw.to_string_dict(self._stroke_delim)
            self._on_new_dictionary(translations)

    def _translated(self, _, new_actions:IPlover.ActionSequence) -> None:
        """ Add Plover user actions to the current translation state with the latest strokes.
            If valid, parse it into strings and call back with them. """
        strokes = self._engine.get_last_strokes()
        new_state = self._state & TranslationState(strokes, new_actions)
        if new_state is not self._state:
            self._state = new_state
            keys, letters = new_state.to_strings(self._stroke_delim)
            if keys and letters:
                self._on_translation(keys, letters)

    @classmethod
    def from_engine(cls, engine:IPlover.Engine, stroke_delim="/") -> "PloverExtension":
        """ Build a new extension object from a Plover <engine>. """
        wrapper = EngineWrapper(engine)
        return cls(wrapper, stroke_delim)


class IncompatibleError(Exception):
    """ Raised if the installed Plover version is not compatible with this application. """


class PloverAppInfo:
    """ Returns information about the user's Plover installation or its files. """

    def __init__(self) -> None:
        # self._app_name = "plover"              # Name of Plover application for finding its user data folder.
        # self._cfg_filename = "plover.cfg"      # Filename for Plover configuration with user dictionaries.
        self._version_required = "4.0.0.dev8"  # Minimum version of Plover required for plugin compatibility.

    def check_compatible(self) -> None:
        """ Check the Plover version to see if it is compatible with this extension. """
        version = self._version_required
        try:
            pkg_resources.working_set.require(f"plover>={version}")
        except pkg_resources.ResolutionError:
            raise IncompatibleError(f"Plover v{version} or greater required.")


plover_info = PloverAppInfo()
