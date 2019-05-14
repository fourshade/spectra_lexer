from functools import partial
from itertools import chain
import pkg_resources
from typing import Optional, Sequence, Tuple

from .app import PLOVERApp
from .types import join_strokes, PloverAction, PloverEngine, PloverStenoDictCollection
from spectra_lexer.core import Component, Command
from spectra_lexer.steno import LXLexer, LXTranslations
from spectra_lexer.steno.translations import TranslationsDictionary
from spectra_lexer.system import SYSControl

# TODO: Import Plover steno system?
# Minimum version of Plover required for plugin compatibility.
_PLOVER_VERSION_REQUIRED = "4.0.0.dev8"
_INCOMPATIBLE_MESSAGE = f"ERROR: Plover v{_PLOVER_VERSION_REQUIRED} or greater required."

# Starting/reset state of translation buffer. Can be safely assigned without copy due to immutability.
_BLANK_STATE = ((), "")


class PLOVERInterface:
    """ Main interface class for Plover. Receives dictionaries and translations from Plover using callbacks. """

    @Command
    def found_dicts(self, steno_dc:PloverStenoDictCollection) -> None:
        """ When new Plover dictionaries are sent, convert them while showing loading messages. """
        raise NotImplementedError

    @Command
    def found_translation(self, _, new_actions:Sequence[PloverAction]) -> None:
        """ When a new translation becomes available, see if it can or should be formatted and sent to the lexer. """
        raise NotImplementedError


class PloverInterface(Component, PLOVERInterface,
                      PLOVERApp.Connect):
    """ Component for specific conversions and compatibility checks on Plover's version number and data types. """

    PLOVER_ENGINE_CONNECTIONS = [("dictionaries_loaded", PLOVERInterface.found_dicts),
                                 ("translated",          PLOVERInterface.found_translation)]

    _plover: PloverEngine = None              # Plover engine. Assumed not to change during run-time.
    _state: Tuple[tuple, str] = _BLANK_STATE  # Current *immutable* set of contiguous strokes and text.

    def on_engine_connect(self, plover_engine:PloverEngine) -> None:
        """ If Plover is not running, make a fake engine. main() will start the event loop in this case. """
        if plover_engine is None:
            self.test()
        elif self._compat_check():
            self._start(plover_engine)

    def test(self, *args, **kwargs) -> PloverEngine:
        """ Make a fake Plover engine and run some simple tests. Return the engine when done. """
        self._start(PloverEngine.test(*args, **kwargs))
        self.found_translation(None, [PloverAction()])
        return self._plover

    def _compat_check(self) -> bool:
        """ If the compatibility check fails, don't try to connect to Plover. Send an error message. """
        try:
            pkg_resources.working_set.require("plover>=" + _PLOVER_VERSION_REQUIRED)
            return True
        except pkg_resources.ResolutionError:
            self.engine_call(SYSControl.status, _INCOMPATIBLE_MESSAGE)
            return False

    def _start(self, plover_engine:PloverEngine) -> None:
        """ Perform initial engine connection and callback/dictionary setup. """
        self._plover = plover_engine
        # Lock the engine thread to be sure the dictionaries aren't written while we're parsing them.
        with plover_engine:
            # Connect Plover engine signals to Spectra commands and convert all current dictionaries.
            for signal, command in self.PLOVER_ENGINE_CONNECTIONS:
                plover_engine.signal_connect(signal, partial(self.engine_call, command))
            self._convert_dicts(plover_engine.dictionaries)

    def found_dicts(self, steno_dc:PloverStenoDictCollection) -> None:
        self.engine_call(SYSControl.status, "Found new Plover dictionaries...")
        self._convert_dicts(steno_dc)
        self.engine_call(SYSControl.status, "Loaded new dictionaries from Plover engine.")

    def _convert_dicts(self, steno_dc:PloverStenoDictCollection) -> TranslationsDictionary:
        """ Plover dictionaries are not proper Python dicts and cannot be handled as such.
            They only have a subset of the normal dict methods. The fastest of these is d.items(). """
        finished_dict = TranslationsDictionary()
        for d in steno_dc.dicts:
            if d and d.enabled:
                if isinstance(next(iter(d.items())), tuple):
                    # If strokes are in tuple form, they must be joined into strings.
                    # The fastest method found in profiling uses a chained alternating iterator.
                    kv_alt = chain.from_iterable(d.items())
                    finished_dict.update(zip(map(join_strokes, kv_alt), kv_alt))
                else:
                    finished_dict.update(d.items())
        self.engine_call(LXTranslations.Dict, finished_dict)
        return finished_dict

    def found_translation(self, _, new_actions:Sequence[PloverAction]) -> None:
        """ Make sure that we have at least one new action and strokes from one new valid translation. """
        t_strokes = self._get_last_strokes_if_valid()
        if not new_actions or not t_strokes:
            self._state = _BLANK_STATE
            return
        # Unpack and use the current state if the new text attaches to it, otherwise start fresh.
        strokes, text = self._state if new_actions[0].prev_attach else _BLANK_STATE
        # Combine all the new strokes and text into the current state and send it to the lexer.
        strokes += t_strokes
        text += "".join(a.text for a in new_actions if a.text)
        self._state = strokes, text
        stroke_string = join_strokes(strokes)
        # User strokes may be composed of all sorts of custom briefs, so do not attempt to match every key.
        self.engine_call(LXLexer.query, stroke_string, text, need_all_keys=False)

    def _get_last_strokes_if_valid(self) -> Optional[Tuple[str]]:
        """ Lock the Plover engine thread to access the Plover translator state.
            Return the newest strokes if they produced valid text, otherwise None. """
        with self._plover:
            try:
                # Get the last translation, if existing and valid.
                t = self._plover.translator_state.translations[-1]
                # It must have produced English text with at least one alphanumeric character.
                if any(map(str.isalnum, t.english)):
                    return t.rtfcre
            except (IndexError, TypeError, ValueError):
                return None
