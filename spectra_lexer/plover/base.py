from functools import partial
from itertools import chain
from typing import Dict, Iterable, Iterator, Optional, Sequence, Tuple

from spectra_lexer import Component, pipe
from spectra_lexer.keys import join_strokes
from spectra_lexer.plover.compat import PloverAction, PloverEngine, PloverStenoDict, PloverStenoDictCollection, \
    compatibility_check, INCOMPATIBLE_MESSAGE


# Starting/reset state of translation buffer. Can be safely assigned without copy due to immutability.
_BLANK_STATE = ((), "")


class PloverPluginInterface(Component):
    """ Main component class for Plover plugin. It is the only class that should directly access Plover's objects.
        Receives and processes dictionaries and translations from Plover using callbacks. """

    ROLE = "plover"

    _plover_engine: PloverEngine = None               # Plover engine. Assumed not to change during run-time.
    _current_state: Tuple[tuple, str] = _BLANK_STATE  # Current *immutable* set of contiguous strokes and text.

    @pipe("start", "new_status")
    def start(self, *, plover_engine=None, **opts) -> str:
        """ Perform initial compatibility check and callback/dictionary setup. """
        # If the compatibility check fails or there's no engine, don't try to connect to Plover. Return an error.
        if not compatibility_check() or plover_engine is None:
            return INCOMPATIBLE_MESSAGE
        self._plover_engine = plover_engine
        # Lock the Plover engine thread, connect everything to it, and load all current dictionaries.
        with self._plover_engine:
            self._plover_connect('dictionaries_loaded', "plover_load_dicts")
            self._plover_connect('translated',          "sig_on_new_translation")
            self.engine_call("plover_load_dicts", self._plover_engine.dictionaries)
        return "Loaded dictionaries from Plover engine."

    def _plover_connect(self, plover_signal:str, spectra_cmd:str) -> None:
        """ Connect a Plover engine signal to a Spectra engine command. """
        self._plover_engine.signal_connect(plover_signal, partial(self.engine_call, spectra_cmd))

    @pipe("plover_load_dicts", "new_translations")
    def load_dicts(self, steno_dc:PloverStenoDictCollection) -> Optional[Dict[str, str]]:
        """ When usable Plover dictionaries become available, parse their items into a standard dict for search. """
        if not steno_dc or not steno_dc.dicts:
            return None
        usable_dicts = [d for d in steno_dc.dicts if d and d.enabled]
        return _parse_and_merge(usable_dicts)

    @pipe("sig_on_new_translation", "lexer_query", unpack=True)
    def on_new_translation(self, _, new_actions:Sequence[PloverAction]) -> Optional[Tuple[str, str]]:
        """ When a new translation becomes available, see if it can or should be formatted and sent to the lexer. """
        # Lock the Plover engine thread to access its state.
        with self._plover_engine:
            t_strokes = _get_last_strokes_if_valid(self._plover_engine)
        # Make sure that we have at least one new action and strokes from one new valid translation.
        if not new_actions or not t_strokes:
            self._current_state = _BLANK_STATE
            return None
        # Unpack and use the current state if the new text attaches to it, otherwise start fresh.
        strokes, text = self._current_state if new_actions[0].prev_attach else _BLANK_STATE
        # Combine all the new strokes and text into the current state and send it to the lexer.
        strokes += t_strokes
        text += "".join(a.text for a in new_actions if a.text)
        self._current_state = strokes, text
        return join_strokes(strokes), text


def _get_last_strokes_if_valid(plover:PloverEngine) -> Optional[Tuple[str]]:
    """ Read the Plover translator state and return the newest strokes if they produced valid text, otherwise None. """
    try:
        # Get the last translation, if existing and valid.
        t = plover.translator_state.translations[-1]
        # It must have produced English text with at least one alphanumeric character.
        if any(map(str.isalnum, t.english)):
            return t.rtfcre
    except (IndexError, TypeError, ValueError):
        return None


def _parse_and_merge(d_iter:Iterable[PloverStenoDict]) -> Dict[str, str]:
    """ Parse and merge items from Plover dictionaries into a single string dict. """
    return dict(chain.from_iterable(map(_parse_items, d_iter)))


def _parse_items(d:PloverStenoDict) -> Iterator[tuple]:
    """ Parse items from a Plover dictionary into string form and return an iterator. """
    # Plover dictionaries are not proper Python dicts and cannot be handled as such.
    # They only have a subset of the standard dict methods. The fastest of these is items().
    if isinstance(next(iter(d)), tuple):
        # If strokes are in tuple form, they must be joined into strings.
        # The fastest method found in profiling uses a single chained iterator called twice per item.
        kv_alt = chain.from_iterable(d.items())
        return zip(map(join_strokes, kv_alt), kv_alt)
    else:
        return d.items()
