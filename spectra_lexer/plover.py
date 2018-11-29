import itertools
import pkg_resources
from typing import Callable, ClassVar, List, Optional, Sequence

from spectra_lexer.display.cascaded_text import CascadedTextDisplay
from spectra_lexer.engine import SpectraEngineComponent, SpectraEngine
from spectra_lexer.file import FileHandler
from spectra_lexer.keys import join_strokes
from spectra_lexer.lexer import StenoLexer
from spectra_lexer.search import SearchEngine

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


class PloverPluginLayer(SpectraEngineComponent):
    """ Compatibility layer for Plover plugin functionality.
        This is the only class that should touch objects passed in by Plover.
        It is the top-level class for plugin functionality; the engine must reside here. """

    # Instance attributes are lost when the container dialog is closed and re-opened.
    # The engine is relatively expensive to create, so save it on the class to retain its state.
    _engine: ClassVar[SpectraEngine] = None

    _plover_engine: PloverEngine            # Plover engine, required to access the most recent translations.
    _last_strokes: List[str]                # Most recent set of contiguous strokes.
    _last_text: List[str]                   # Most recent text output from those strokes.

    def __init__(self, plover_engine:PloverEngine, *, gui:SpectraEngineComponent):
        if self._engine is None:
            # Load the engine only once, the first time the window is opened, and store it on the class.
            PloverPluginLayer._engine = SpectraEngine(FileHandler(), StenoLexer(), SearchEngine(),
                                                      CascadedTextDisplay(), gui, self)
            self._engine.start()
            # If the calling version of Plover is incompatible, don't connect its callbacks.
            # Instead, show an error message and prevent any further interaction with Plover.
            if not self._compatibility_check():
                return
            # Only attempt to load a fresh copy of the dicts if the engine wasn't loaded before.
            self.parse_dict_collection(plover_engine.dictionaries)
        else:
            # Connect the new GUI and this object to the existing engine, overwriting the old ones.
            self._engine.connect(gui, self, overwrite=True)
        # Send command to set up anything else that needs it for a new GUI.
        self._engine.send("new_window")
        # If everything else turned out good, connect this component to the Plover engine and await callbacks.
        self._plover_engine = plover_engine
        self._last_strokes = []
        self._last_text = []
        plover_engine.signal_connect('dictionaries_loaded', self.parse_dict_collection)
        plover_engine.signal_connect('translated', self.parse_translations)

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
            self.engine_send("search_set_dict", merged)

    def parse_translations(self, _, new:Sequence[PloverAction]) -> None:
        new_strokes = []
        new_text = []
        with self._plover_engine:
            t_list = self._plover_engine.translator_state.translations
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
            # Combine the strokes and text into single strings, make a lexer query, and display the results.
            self.engine_send("lexer_query", join_strokes(new_strokes), "".join(new_text))
        # Reset the "previous" variables for next time. If we skipped the analysis due to a bad translation or
        # action, the new variables will still be blank, so this resets everything to empty.
        self._last_strokes = new_strokes
        self._last_text = new_text

    def _compatibility_check(self) -> bool:
        """ Return True only if a compatible version of Plover is found in the working set. """
        try:
            pkg_resources.working_set.require("plover>="+_PLOVER_VERSION_REQUIRED)
            return True
        except pkg_resources.ResolutionError:
            self.engine_send("gui_show_status_message",
                             "ERROR: Plover v{} or greater required.".format(_PLOVER_VERSION_REQUIRED))
            return False
