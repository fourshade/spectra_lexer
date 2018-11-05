import itertools
from typing import Callable, List, Optional, Sequence

from spectra_lexer.keys import join_strokes

# Class structures that specify a minimum level of functionality for compatibility with Plover.

class PloverStenoDict:
    enabled: bool
    items: Callable

class PloverStenoDictCollection:
    dicts: Sequence[PloverStenoDict]

class PloverAction:
    prev_attach: bool
    text: Optional[str]

class PloverTranslation:
    rtfcre: tuple
    english: Optional[str]

class PloverTranslatorState:
    translations: Sequence[PloverTranslation]

class PloverEngine:
    dictionaries: PloverStenoDictCollection
    translator_state: PloverTranslatorState
    signal_connect: Callable


class PloverPluginLayer:
    """ Compatibility layer for Plover plugin functionality.
        This is the only class that should touch objects passed in by Plover. """

    _engine = PloverEngine                      # Plover engine, required to access the most recent translations.
    _last_strokes: List[str]                    # Most recent set of contiguous strokes.
    _last_text: List[str]                       # Most recent text output from those strokes.
    _dict_callback: Callable[[dict], None]      # GUI callback to replace the search dictionary.
    _out_callback: Callable[[str, str], None]   # GUI callback to make a new lexer query.

    def __init__(self, engine:PloverEngine, dict_callback:Callable, out_callback:Callable):
        self._engine = engine
        self._last_strokes = []
        self._last_text = []
        self._dict_callback = dict_callback
        self._out_callback = out_callback
        # The engine is currently setting this object up, so we do not need to lock its thread.
        self.parse_dict_collection(engine.dictionaries)
        self._engine.signal_connect('dictionaries_loaded', self.parse_dict_collection)
        self._engine.signal_connect('translated', self.parse_translations)

    def parse_dict_collection(self, steno_dc:PloverStenoDictCollection) -> None:
        """ When Plover dictionaries become available, merge them all into a standard dict for the main lexer window.
            If strokes are in tuple form, they must be joined with stroke separators into ordinary strings. """
        if steno_dc and steno_dc.dicts:
            merged = {}
            for d in steno_dc.dicts:
                if d and d.enabled:
                    if isinstance(next(iter(d.items()))[0], tuple):
                        kv_alt = itertools.chain.from_iterable(d.items())
                        merged.update(zip(map(join_strokes, kv_alt), kv_alt))
                    else:
                        merged.update(d.items())
            self._dict_callback(merged)

    def parse_translations(self, old:Sequence[PloverAction], new:Sequence[PloverAction]) -> None:
        new_strokes = []
        new_text = []
        with self._engine:
            t_list = self._engine.translator_state.translations
            t = t_list[-1] if t_list else None
        # Make sure that we have at least one new action and one recent translation.
        # That translation must have an English mapping with at least one alphanumeric character.
        if new and t and t.english and any(map(str.isalnum, t.english)):
            # If this action attaches to the previous one, start with the strokes and text from the last analysis.
            if new[0].prev_attach:
                new_strokes = self._last_strokes
                new_text = self._last_text
            # Extend lists with all strokes from the given translation and text from all the given actions.
            new_strokes.extend(t.rtfcre)
            new_text.extend(a.text for a in new if a.text)
            # Combine the strokes and text into single strings and send them to the lexer widget for processing.
            self._out_callback(join_strokes(new_strokes), "".join(new_text))
        # Reset the "previous" variables for next time. If we skipped the analysis due to a bad translation or
        # action, the new variables will still be blank, so this resets everything to empty.
        self._last_strokes = new_strokes
        self._last_text = new_text
