""" Main module for the Plover plugin components. """

from configparser import ConfigParser
from functools import partial
import json
import os
from typing import Callable, Dict, Iterable, Optional, Sequence, Tuple

from spectra_lexer.resource.translations import RTFCREDict
from spectra_lexer.util.path import UserPathConverter


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

    def __init__(self, engine:IPlover.Engine, *, stroke_delim="/") -> None:
        self._engine = EngineWrapper(engine)  # Wrapped Plover engine object.
        self._stroke_delim = stroke_delim     # Delimiter for Plover stroke strings.
        self._state = TranslationState()      # Contains current user strokes and actions.

    def call_on_dictionaries_loaded(self, callback:Callable[[IPlover.StenoDictCollection], None]) -> None:
        """ Set a callback to receive dictionaries when Plover loads them (happens on startup, reordering, etc.) """
        self._engine.signal_connect("dictionaries_loaded", callback)

    def call_on_translated(self, callback:Callable[[IPlover.ActionSequence, IPlover.ActionSequence], None]) -> None:
        """ Set a callback to receive user input actions. """
        self._engine.signal_connect("translated", callback)

    def parse_dictionaries(self, steno_dc:IPlover.StenoDictCollection=None) -> RTFCREDict:
        """ Convert and merge all translations in <steno_dc> into an RTFCREDict.
            If None, convert the current set of dictionaries from the engine. """
        if steno_dc is None:
            steno_dc = self._engine.get_dictionaries()
        d_raw = self._engine.compile_raw_dict(steno_dc)
        return d_raw.to_string_dict(self._stroke_delim)

    def parse_actions(self, _:IPlover.ActionSequence, new_actions:IPlover.ActionSequence) -> Optional[Tuple[str, str]]:
        """ Add new Plover user actions to the current translation state with the latest strokes.
            If invalid or unchanged, return None. Otherwise, parse it into strings and return them. """
        strokes = self._engine.get_last_strokes()
        new_state = self._state & TranslationState(strokes, new_actions)
        if new_state is not self._state:
            self._state = new_state
            keys, letters = new_state.to_strings(self._stroke_delim)
            if keys and letters:
                return keys, letters


class IncompatibleError(Exception):
    """ Raised if the installed Plover version is not compatible with this application. """


class PloverAppInfo:
    """ Returns information about the user's Plover installation or its files. """

    def __init__(self, *, app_name:str, cfg_filename:str, min_version:str) -> None:
        self._app_name = app_name          # Name of Plover application for finding its user data folder.
        self._cfg_filename = cfg_filename  # Filename for Plover configuration with user dictionaries.
        self._min_version = min_version    # Minimum version of Plover required for plugin compatibility.

    def check_compatible(self) -> None:
        """ Check the Plover version to see if it is compatible with this extension. """
        # pkg_resources takes 4x as long to import as *everything else combined*. Only import it when/if we need it.
        import pkg_resources
        try:
            pkg_resources.working_set.require(f"plover>={self._min_version}")
        except pkg_resources.ResolutionError as e:
            raise IncompatibleError(f"Plover v{self._min_version} or greater required.") from e

    def user_dictionary_files(self, *, ignore_errors=False) -> Sequence[str]:
        """ Search the user's local app data for the Plover config file and find the dictionary files.
            Return an empty list on a file or parsing error if <ignore_errors> is True. """
        try:
            return self._find_dictionaries()
        except (IndexError, KeyError, OSError, ValueError):
            if not ignore_errors:
                raise
            return []

    def _find_dictionaries(self) -> Sequence[str]:
        """ Search the user's local app data for the Plover config file.
            Parse the dictionaries section and return the filenames for all dictionaries in order. """
        converter = UserPathConverter(self._app_name)
        cfg_filename = converter.convert(self._cfg_filename)
        parser = ConfigParser()
        with open(cfg_filename, 'r', encoding='utf-8') as fp:
            parser.read_file(fp)
        # Dictionaries are located in the same directory as the config file.
        # The config value we need is read as a string, but it must be decoded as a JSON array of objects.
        value = parser['System: English Stenotype']['dictionaries']
        dictionary_specs = json.loads(value)
        plover_dir = os.path.split(cfg_filename)[0]
        # Earlier keys override later ones in Plover, but dict.update does the opposite. Reverse the priority order.
        return [os.path.join(plover_dir, spec['path']) for spec in reversed(dictionary_specs)]


# Global import for compatibility checks and user data.
plover_info = PloverAppInfo(app_name="plover",
                            cfg_filename="plover.cfg",
                            min_version="4.0.0.dev8")
