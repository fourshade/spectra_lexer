import itertools
import pkg_resources
from typing import Callable, ClassVar, List, Optional, Sequence

from spectra_lexer.keys import join_strokes

# Minimum version of Plover required for plugin compatibility.
_PLOVER_VERSION_REQUIRED = "4.0.0.dev8"

# Partial class structures that specify a minimum level of functionality for compatibility with Plover.
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

    _window_opened: ClassVar[bool] = False      # Has a window been opened before by an instance of this class?

    _engine = PloverEngine                      # Plover engine, required to access the most recent translations.
    _last_strokes: List[str]                    # Most recent set of contiguous strokes.
    _last_text: List[str]                       # Most recent text output from those strokes.
    _dict_callback: Callable[[dict], None]      # GUI callback to replace the search dictionary.
    _out_callback: Callable[[str, str], None]   # GUI callback to make a new lexer query.
    _msg_callback: Callable[[str], None]        # GUI callback to display a status message.

    def __init__(self, engine:PloverEngine, dict_callback:Callable, out_callback:Callable, msg_callback:Callable):
        # If the calling version of Plover is incompatible, don't register the callbacks.
        # Instead, show an error message and prevent any further interaction with Plover.
        if not _compatibility_check():
            msg_callback("ERROR: Plover v{} or greater required.".format(_PLOVER_VERSION_REQUIRED))
            return
        self._engine = engine
        self._last_strokes = []
        self._last_text = []
        self._dict_callback = dict_callback
        self._out_callback = out_callback
        self._msg_callback = msg_callback
        self._engine.signal_connect('dictionaries_loaded', self.parse_dict_collection)
        self._engine.signal_connect('translated', self.parse_translations)
        # Only load a fresh copy of the dicts if a window wasn't opened before.
        if not PloverPluginLayer._window_opened:
            self.parse_dict_collection(engine.dictionaries)
            PloverPluginLayer._window_opened = True

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
            t_strokes, t_text = (t.rtfcre, t.english) if t else (None, None)
        # Make sure that we have at least one new action and one recent translation.
        # That translation must have an English mapping with at least one alphanumeric character.
        if new and t_text and any(map(str.isalnum, t_text)):
            # If this action attaches to the previous one, start with the strokes and text from the last analysis.
            if new[0].prev_attach:
                new_strokes = self._last_strokes
                new_text = self._last_text
            # Extend lists with all strokes from the given translation and text from all the given actions.
            new_strokes.extend(t_strokes)
            new_text.extend(a.text for a in new if a.text)
            # Combine the strokes and text into single strings and send them to the lexer widget for processing.
            self._out_callback(join_strokes(new_strokes), "".join(new_text))
        # Reset the "previous" variables for next time. If we skipped the analysis due to a bad translation or
        # action, the new variables will still be blank, so this resets everything to empty.
        self._last_strokes = new_strokes
        self._last_text = new_text


def _compatibility_check():
    """ Return True only if a compatible version of Plover is found in the working set. """
    try:
        pkg_resources.working_set.require("plover>="+_PLOVER_VERSION_REQUIRED)
        return True
    except pkg_resources.ResolutionError:
        return False
