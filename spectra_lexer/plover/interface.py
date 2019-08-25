from typing import Callable, Dict, Sequence

from .types import join_strokes, PloverAction, PloverEngine, PloverStenoDictCollection


class PloverInterface:
    """ Main interface class for Plover. Receives dictionaries and translations from Plover using callbacks. """

    _engine: PloverEngine = PloverEngine()
    _dict_callback: Callable[[Dict[str, str]], None]
    _query_callback: Callable[[Sequence[str]], None]
    _translation: Sequence[str]  # Current set of contiguous strokes and text.

    def __init__(self, dict_callback:Callable, query_callback:Callable):
        self._dict_callback = dict_callback
        self._query_callback = query_callback
        self._reset()

    def connect(self, engine:PloverEngine) -> None:
        """ Connect all Plover engine signals to methods, which only call the callbacks on success. """
        self._engine = engine
        engine.signal_connect("dictionaries_loaded", self.convert_dicts)
        engine.signal_connect("translated", self.parse_translation)
        # Convert the current set of dictionaries from the engine to finish.
        self.convert_dicts(engine.dictionaries)

    def convert_dicts(self, steno_dc:PloverStenoDictCollection) -> None:
        """ Plover dictionaries are not proper Python dicts and cannot be handled as such.
            They only have a subset of the normal dict methods. The fastest of these is .items().
            As a plugin, we lock the Plover engine just long enough to copy these with dict().
            The contents are strings and tuples, so we are thread-safe after this point. """
        with self._engine:
            dicts = [dict(d.items()) for d in steno_dc.dicts if d and d.enabled]
        if not dicts:
            return None
        # Strokes in tuple form must be joined into strings.
        converted_dict = {}
        for d in dicts:
            converted_dict.update(zip(map(join_strokes, d), d.values()))
        self._dict_callback(converted_dict)

    def parse_translation(self, _, new_actions:Sequence[PloverAction]) -> None:
        """ Process a Plover translation into standard data types and send it to the next component.
            Make sure that we have at least one new action and strokes from one new valid translation. """
        strokes = self._get_last_strokes()
        if not strokes:
            self._reset()
            return
        # The strokes must have produced English text with at least one alphanumeric character.
        text = "".join([a.text for a in new_actions if a.text])
        if not any(map(str.isalnum, text)):
            self._reset()
            return
        # Use the current state if the new text attaches to it, otherwise start fresh.
        if not any([a.prev_attach for a in new_actions]):
            self._reset()
        self._combine(strokes, text)
        self._query_callback(self._translation)

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
        self._translation = ["", ""]

    def _combine(self, new_strokes:Sequence[str], new_text:str) -> None:
        """ Combine all new strokes and text into the current state. """
        strokes, text = self._translation
        new_strokes = filter(None, [strokes, *new_strokes])
        self._translation = [join_strokes(new_strokes), text + new_text]

    def test(self, *args, **kwargs) -> None:
        """ Make a fake Plover engine and run some simple tests. Do not check for compatibility. """
        self.connect(PloverEngine.test(*args, **kwargs))
        self.parse_translation(None, [PloverAction()])
