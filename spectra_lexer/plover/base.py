from typing import Sequence

from .types import PloverAction, PloverEngine, PloverStenoDictCollection
from spectra_lexer.core import Command
from spectra_lexer.gui_qt import GUIQT


class PLOVER(GUIQT):

    @Command
    def EngineReady(self, engine:PloverEngine) -> None:
        """ Send this command with the Plover engine as soon as the components are connected. """
        raise NotImplementedError

    @Command
    def FoundDicts(self, steno_dc:PloverStenoDictCollection) -> None:
        """ When new Plover dictionaries are sent, unpack them into Python dicts and parse them. """
        raise NotImplementedError

    @Command
    def FoundTranslation(self, _, new_actions:Sequence[PloverAction]) -> None:
        """ When a new translation becomes available, unpack it and send it to the translations processor. """
        raise NotImplementedError
