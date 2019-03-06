from functools import partial
from itertools import chain
from typing import Dict, Optional, Sequence, Tuple

from spectra_lexer import Component
from spectra_lexer.keys import join_strokes
from spectra_lexer.plover.compat import compatibility_check, INCOMPATIBLE_MESSAGE, PloverAction, PloverEngine, \
    PloverStenoDictCollection, PloverTranslatorState

# Starting/reset state of translation buffer. Can be safely assigned without copy due to immutability.
_BLANK_STATE = ((), "")


class PloverInterface(Component):
    """ Main component class for Plover plugin. It is the only class that should directly access Plover's objects.
        Receives and processes dictionaries and translations from Plover using callbacks. """

    _plover: PloverEngine = None              # Plover engine. Assumed not to change during run-time.
    _state: Tuple[tuple, str] = _BLANK_STATE  # Current *immutable* set of contiguous strokes and text.

    @pipe("new_plover_engine", "plover_parse_dicts")
    def start(self, plover_engine:PloverEngine) -> Optional[PloverStenoDictCollection]:
        """ Perform initial compatibility check and callback/dictionary setup. """
        self._plover = plover_engine
        # If the compatibility check fails, don't try to connect to Plover. Return an error.
        if not compatibility_check():
            self.engine_call("new_status", INCOMPATIBLE_MESSAGE)
            return None
        # Connect all commands to the Plover engine and load all current dictionaries.
        self._plover_connect({"dictionaries_loaded": "plover_parse_dicts", "translated": "plover_new_translation"})
        return plover_engine.dictionaries

    def _plover_connect(self, connections:Dict[str, str]) -> None:
        """ Connect Plover engine signals to Spectra engine commands. """
        with self._plover:
            for signal, cmd in connections.items():
                self._plover.signal_connect(signal, partial(self.engine_call, cmd))

    @pipe("plover_parse_dicts", "new_translations")
    def parse_dicts(self, steno_dc:PloverStenoDictCollection) -> Dict[str, str]:
        """ When usable Plover dictionaries become available, parse their items into a standard dict for search. """
        self.engine_call("new_status", "Loading dictionaries...")
        # Lock the engine thread to be sure the dictionaries aren't written while we're parsing them.
        with self._plover:
            finished_dict = _parse_and_merge(steno_dc)
        self.engine_call("new_status", "Loaded dictionaries from Plover engine.")
        return finished_dict

    @pipe("plover_new_translation", "lexer_query")
    def on_new_translation(self, _, new_actions:Sequence[PloverAction]) -> Optional[Tuple[str, str]]:
        """ When a new translation becomes available, see if it can or should be formatted and sent to the lexer. """
        # Lock the Plover engine thread to access its state.
        with self._plover:
            t_strokes = _get_last_strokes_if_valid(self._plover.translator_state)
        # Make sure that we have at least one new action and strokes from one new valid translation.
        if not new_actions or not t_strokes:
            self._state = _BLANK_STATE
            return None
        # Unpack and use the current state if the new text attaches to it, otherwise start fresh.
        strokes, text = self._state if new_actions[0].prev_attach else _BLANK_STATE
        # Combine all the new strokes and text into the current state and send it to the lexer.
        strokes += t_strokes
        text += "".join(a.text for a in new_actions if a.text)
        self._state = strokes, text
        return join_strokes(strokes), text


def _get_last_strokes_if_valid(translator_state:PloverTranslatorState) -> Optional[Tuple[str]]:
    """ Read the Plover translator state and return the newest strokes if they produced valid text, otherwise None. """
    try:
        # Get the last translation, if existing and valid.
        t = translator_state.translations[-1]
        # It must have produced English text with at least one alphanumeric character.
        if any(map(str.isalnum, t.english)):
            return t.rtfcre
    except (IndexError, TypeError, ValueError):
        return None


def _parse_and_merge(steno_dc:PloverStenoDictCollection) -> Dict[str, str]:
    """ Parse and merge items from a Plover dictionary collection into a single string dict.
        Plover dictionaries are not proper Python dicts and cannot be handled as such.
        They only have a subset of the normal dict methods. The fastest of these is d.items(). """
    finished_dict = {}
    for d in steno_dc.dicts:
        if d and d.enabled:
            if isinstance(next(iter(d.items())), tuple):
                # If strokes are in tuple form, they must be joined into strings.
                # The fastest method found in profiling uses a chained alternating iterator.
                kv_alt = chain.from_iterable(d.items())
                finished_dict.update(zip(map(join_strokes, kv_alt), kv_alt))
            else:
                finished_dict.update(d.items())
    return finished_dict
