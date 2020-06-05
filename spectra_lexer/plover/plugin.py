""" Main module for the Plover plugin components. """

from functools import partial
from typing import Tuple, Dict, Optional, Sequence, Callable, Iterable

StrokeTuple = Tuple[str, ...]            # Tuple of RTFCRE strokes.
TupleStenoDict = Dict[StrokeTuple, str]  # Dict of tuple-keyed Plover translations.
StringStenoDict = Dict[str, str]         # Dict of string-keyed Plover translations.


class IPlover:
    """ Data types and interfaces containing only what is necessary for compatibility with Plover. """

    VERSION = "4.0.0.dev8"  # Plover version for which these interfaces are known to be valid.

    class IncompatibleError(Exception):
        """ Raised if the installed Plover version is not compatible with this application. """

    @classmethod
    def is_compatible(cls) -> None:
        """ Check the Plover version to see if it is compatible with this extension. """
        # pkg_resources takes 4x as long to import as *everything else combined*. Only import it when/if we need it.
        import pkg_resources
        try:
            pkg_resources.working_set.require(f"plover>={cls.VERSION}")
        except pkg_resources.ResolutionError as e:
            raise cls.IncompatibleError(f"Plover v{cls.VERSION} or greater required.") from e

    class Action:
        prev_attach: bool
        prev_replace: Optional[str]
        text: Optional[str]

    ActionSequence = Sequence[Action]

    class Translation:
        rtfcre: StrokeTuple
        english: Optional[str]

    class TranslatorState:
        translations: Sequence["IPlover.Translation"]

    class StenoDictionary:
        items: Callable[[], Iterable[Tuple[StrokeTuple, str]]]
        enabled: bool

    class StenoDictionaryCollection:
        dicts: Sequence["IPlover.StenoDictionary"]

    class Engine:
        dictionaries: "IPlover.StenoDictionaryCollection"
        translator_state: "IPlover.TranslatorState"
        signal_connect: Callable[[str, Callable], None]
        __enter__: Callable[[], None]
        __exit__: Callable[..., bool]


def steno_dc_to_dict(steno_dc:IPlover.StenoDictionaryCollection) -> TupleStenoDict:
    """ Return a normal Python dict updated with items from <steno_dc> in reverse order of precedence.
        Plover dictionaries only have a subset of the normal dict methods. The fastest of these is .items(). """
    d = {}
    for steno_d in reversed(steno_dc.dicts):
        if steno_d and steno_d.enabled:
            d.update(steno_d.items())
    return d


class EngineWrapper:
    """ Connects signals and transfers data from the Plover engine in a thread-safe manner. """

    def __init__(self, engine:IPlover.Engine) -> None:
        self._engine = engine  # Engine object, either from Plover or a fake for testing.

    def signal_connect(self, key:str, callback:Callable) -> None:
        """ Connect a Plover engine signal to a callback.
            The callback must be wrapped in a partial for signals to reach it...no idea why. """
        self._engine.signal_connect(key, partial(callback))

    def compile_dictionaries(self) -> TupleStenoDict:
        """ As a plugin, we lock the Plover engine just long enough to copy its current steno dictionaries.
            The contents are strings and tuples of strings, so we are thread-safe after this point. """
        with self._engine:
            steno_dc = self._engine.dictionaries
            return steno_dc_to_dict(steno_dc)

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

    def is_attachment(self) -> bool:
        """ Return True if each piece of text attaches to the previous text. """
        for a in self._actions:
            if a.text and not a.prev_attach:
                return False
        return True

    def __len__(self) -> int:
        return len(self._strokes)

    def __add__(self, other:"TranslationState") -> "TranslationState":
        """ Add two translation states together. """
        strokes = [*self._strokes, *other._strokes]
        actions = [*self._actions, *other._actions]
        return self.__class__(strokes, actions)

    def to_strings(self, stroke_delim:str) -> Tuple[str, str]:
        """ Return the string values of this translation state. """
        keys = stroke_delim.join(self._strokes)
        letters_list = []
        for a in self._actions:
            if a.prev_replace:
                letters_list = letters_list[:-len(a.prev_replace)]
            if a.text:
                letters_list += a.text
        letters = "".join(letters_list).strip()
        return keys, letters


class PloverExtension:

    def __init__(self, engine:EngineWrapper, *, stroke_delim="/", stroke_limit=10000) -> None:
        self._engine = engine              # Wrapped Plover engine object.
        self._stroke_delim = stroke_delim  # Delimiter for Plover stroke strings.
        self._stroke_limit = stroke_limit  # Maximum number of strokes/actions to keep in memory, if any.
        self._state = None                 # Contains current user strokes and actions.

    def call_on_dictionaries_loaded(self, callback:Callable[[IPlover.StenoDictionaryCollection], None]) -> None:
        """ Set a callback to receive dictionaries when Plover loads them (happens on startup, reordering, etc.) """
        self._engine.signal_connect("dictionaries_loaded", callback)

    def call_on_translated(self, callback:Callable[[IPlover.ActionSequence, IPlover.ActionSequence], None]) -> None:
        """ Set a callback to receive user input actions. """
        self._engine.signal_connect("translated", callback)

    def parse_dictionaries(self, steno_dc:IPlover.StenoDictionaryCollection=None) -> StringStenoDict:
        """ Convert and merge all translations in <steno_dc> into a string dict.
            If None, convert the current set of dictionaries from the engine. """
        if steno_dc is None:
            d_tuple = self._engine.compile_dictionaries()
        else:
            d_tuple = steno_dc_to_dict(steno_dc)
        keys_iter = map(self._stroke_delim.join, d_tuple)
        items_iter = zip(keys_iter, d_tuple.values())
        return dict(items_iter)

    def parse_actions(self, old_actions:IPlover.ActionSequence,
                      new_actions:IPlover.ActionSequence) -> Optional[Tuple[str, str]]:
        """ Add new Plover user actions to the current translation state with the latest strokes.
            If invalid (empty strokes or text), return None. Otherwise, return the strokes and text as strings. """
        strokes = self._engine.get_last_strokes()
        old_state = self._state
        new_state = TranslationState(strokes, new_actions)
        # Only combine states if there were no deletions, all the new text attaches, and the stroke limit is met.
        if old_state is not None and not old_actions and new_state.is_attachment():
            if len(old_state) + len(new_state) <= self._stroke_limit:
                new_state = old_state + new_state
        keys, letters = new_state.to_strings(self._stroke_delim)
        if keys and letters:
            self._state = new_state
            return keys, letters
        else:
            self._state = None
            return None
