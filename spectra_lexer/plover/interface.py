from typing import Sequence

from .base import PLOVER
from .types import join_strokes, PloverAction, PloverStenoDictCollection, PloverTranslationsDictionary


class PloverInterface(PLOVER):
    """ Main interface class for Plover. Receives dictionaries and translations from Plover using callbacks. """

    _translation: Sequence[str]  # Current set of contiguous strokes and text.

    def __init__(self):
        super().__init__()
        self._reset()

    def FoundDicts(self, steno_dc:PloverStenoDictCollection) -> None:
        """ Plover dictionaries are not proper Python dicts and cannot be handled as such.
            They only have a subset of the normal dict methods. The fastest of these is .items().
            As a worker thread, we lock the Plover engine just long enough to copy these with dict().
            The contents are strings and tuples, so we are thread-safe after this point. """
        with self.PLOVER_ENGINE:
            dicts = [dict(d.items()) for d in steno_dc.dicts if d and d.enabled]
        if dicts:
            self.TRANSLATIONS = PloverTranslationsDictionary(dicts)
            self.SYSStatus("Loaded new dictionaries from Plover engine.")

    def FoundTranslation(self, _, new_actions:Sequence[PloverAction]) -> None:
        """ Process a Plover translation into standard data types and send it to the next component.
            Make sure that we have at least one new action and strokes from one new valid translation. """
        # TODO: Import Plover steno system?
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
        self._send()

    def _get_last_strokes(self) -> Sequence[str]:
        """ Lock the Plover engine thread to access the Plover translator state and get the newest strokes. """
        engine = self.PLOVER_ENGINE
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

    def _send(self) -> None:
        """ User strokes may be composed of all sorts of custom briefs, so do not attempt to match every key. """
        self.GUIQTUpdate(graph_translation=self._translation)  # TODO: need_all_keys=False
        self.GUIQTAction("VIEWQuery")
