from typing import Dict, Optional, Sequence, Tuple

from .types import join_strokes, PloverAction, PloverEngine, PloverStenoDictCollection


class PloverTranslationParser:
    """ Parses dictionaries and translations from Plover. """

    _engine: PloverEngine          # Engine object, either from Plover or a fake for testing.
    _translation: Tuple[str, str]  # Current set of contiguous strokes and text.

    def __init__(self, engine:PloverEngine) -> None:
        self._engine = engine
        self._reset()

    def convert_dicts(self, steno_dc:PloverStenoDictCollection=None) -> Dict[str, str]:
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
            converted_dict.update(zip(map(join_strokes, d), d.values()))
        return converted_dict

    def parse_translation(self, _, new_actions:Sequence[PloverAction]) -> Optional[Tuple[str, str]]:
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
        self._translation = join_strokes(new_strokes), text + new_text
