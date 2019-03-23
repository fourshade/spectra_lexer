from functools import partial
from typing import Optional, Sequence, Tuple

from .compat import join_strokes
from .types import PloverAction, PloverEngine, PloverTranslatorState, PloverStenoDictCollection
from spectra_lexer import Component

# Starting/reset state of translation buffer. Can be safely assigned without copy due to immutability.
_BLANK_STATE = ((), "")


class PloverInterface(Component):
    """ Main interface class for Plover. Receives dictionaries and translations from Plover using callbacks. """

    _plover: PloverEngine = None              # Plover engine. Assumed not to change during run-time.
    _state: Tuple[tuple, str] = _BLANK_STATE  # Current *immutable* set of contiguous strokes and text.

    @on("new_plover_engine")
    def start(self, plover_engine:PloverEngine) -> None:
        """ Perform initial engine connection and callback/dictionary setup. """
        self._plover = plover_engine
        # Lock the engine thread to be sure the dictionaries aren't written while we're parsing them.
        with plover_engine:
            # Connect Plover engine signals to Spectra commands and convert all current dictionaries.
            for signal, command in ("dictionaries_loaded", "plover_new_dicts"), \
                                   ("translated",          "plover_new_translation"):
                plover_engine.signal_connect(signal, partial(self.engine_call, command))
            self.engine_call("plover_convert_dicts", plover_engine.dictionaries)

    @on("plover_new_dicts")
    def convert_dicts(self, steno_dc:PloverStenoDictCollection) -> None:
        """ When new Plover dictionaries are sent after startup, show loading messages. """
        self.engine_call("new_status", "Found new Plover dictionaries...")
        self.engine_call("plover_convert_dicts", steno_dc)
        self.engine_call("new_status", "Loaded new dictionaries from Plover engine.")

    @on("plover_new_translation", pipe_to="lexer_query")
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
