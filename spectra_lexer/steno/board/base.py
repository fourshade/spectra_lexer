""" Module for generating steno board diagram elements and descriptions. """

from functools import lru_cache

from .elements import XMLElementDict
from .generator import BoardGenerator
from ..base import LX
from spectra_lexer.resource import StenoRule


class BoardRenderer(LX):
    """ Creates graphics for the board diagram. """

    _DEFAULT_RATIO: float = 100.0  # If no aspect ratio is given, this ensures that all boards end up in one row.

    _generator: BoardGenerator = None

    def Load(self) -> None:
        """ Parse the board XML into individual steno key/rule elements. """
        defs = self.BOARD_DEFS
        bounds = defs["bounds"]
        xml_dict = XMLElementDict(defs)
        xml_dict.add_recursive(self.BOARD_ELEMS)
        layout = self.LAYOUT
        self._generator = BoardGenerator(xml_dict, bounds, layout.from_rtfcre, layout.SEP, self.RULES)

    @lru_cache(maxsize=256)
    def LXBoardFromKeys(self, keys:str, ratio:float=_DEFAULT_RATIO) -> bytes:
        """ Generate a board diagram from keys. This isn't cheap, so the most recent ones are cached. """
        return self._generator.from_keys(keys, ratio)

    @lru_cache(maxsize=256)
    def LXBoardFromRule(self, rule:StenoRule, ratio:float=_DEFAULT_RATIO) -> bytes:
        """ Generate a board diagram from a rule. This isn't cheap, so the most recent ones are cached. """
        return self._generator.from_rule(rule, ratio)
