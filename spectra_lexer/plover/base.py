from typing import Sequence

from .types import PloverAction, PloverEngine, PloverStenoDictCollection
from spectra_lexer.core import Command, Resource
from spectra_lexer.gui_qt import GUIQT


class PLOVER(GUIQT):

    PLOVER_ENGINE: PloverEngine = Resource()  # Plover engine. Assumed not to change during run-time.

    @Command
    def FoundDicts(self, steno_dc:PloverStenoDictCollection) -> None:
        """ When new Plover dictionaries are sent, unpack them into Python dicts and parse them. """
        raise NotImplementedError

    @Command
    def FoundTranslation(self, _, new_actions:Sequence[PloverAction]) -> None:
        """ When a new translation becomes available, unpack it and send it to the translations processor. """
        raise NotImplementedError
