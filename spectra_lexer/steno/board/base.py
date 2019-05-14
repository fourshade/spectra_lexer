""" Module for generating steno board diagram elements and descriptions. """

from .elements import XMLElementDict
from .generator import BoardGenerator
from ..base import LX
from spectra_lexer.resource import StenoRule
from spectra_lexer.types.codec import JSONDict

_DEFAULT_RATIO = 100.0  # If no aspect ratio is given, this ensures that all boards end up in one row.

_DEFS_ASSET_PATH = ":/assets/board_defs.json"  # File with board shape definitions.
_BOUNDS_DEF = "bounds"


class BoardRenderer(LX):
    """ Creates graphics for the board diagram. """

    _generator: BoardGenerator = None

    def Load(self) -> None:
        """ Parse the board XML into individual steno key/rule elements. """
        defs = self.SYSFileLoad(JSONDict, _DEFS_ASSET_PATH)
        bounds = defs[_BOUNDS_DEF]
        xml_dict = XMLElementDict(defs)
        xml_dict.add_recursive(self.BOARD)
        layout = self.LAYOUT
        self._generator = BoardGenerator(xml_dict, bounds, layout.from_rtfcre, layout.SEP, self.RULES)

    def LXBoardFromKeys(self, keys:str, ratio:float=_DEFAULT_RATIO) -> bytes:
        if self._generator is None:
            return b""
        return self._generator.from_keys(keys, ratio)

    def LXBoardFromRule(self, rule:StenoRule, ratio:float=_DEFAULT_RATIO) -> bytes:
        if self._generator is None:
            return b""
        return self._generator.from_rule(rule, ratio)
