""" Module for generating steno board diagram elements and descriptions. """

import json

from .elements import XMLElementDict
from .generator import BoardGenerator, STROKE_SENTINEL
from .matcher import KeyMatcher, RuleMatcher
from ..rules import StenoRule
from ..system import LXSystem
from spectra_lexer.core import COREApp, Component, Signal
from spectra_lexer.system import ConsoleCommand, SYSFile

# If no aspect ratio is given, this ensures that all boards end up in one row.
_DEFAULT_RATIO = 100.0

_DEFS_ASSET_PATH = ":/assets/board_defs.json"  # File with board shape definitions.
_BOUNDS_DEF = "bounds"
_BASE_TAG = "base"
_SINGLE_TAG = "key"
_UNMATCHED_TAG = "qkey"
_RULE_TAG = "rule"


class LXBoard:

    @ConsoleCommand("board_from_keys")
    def from_keys(self, keys:str, ratio:float=_DEFAULT_RATIO) -> bytes:
        """ Generate board diagram layouts arranged in columns according to <ratio> from a set of steno keys. """
        raise NotImplementedError

    @ConsoleCommand("board_from_rule")
    def from_rule(self, rule:StenoRule, ratio:float=_DEFAULT_RATIO, *, show_compound:bool=True) -> bytes:
        """ Generate board diagram layouts arranged in columns according to <ratio> from a steno rule.
            If <show_compound> is True, special keys may be shown corresponding to certain named rules. """
        raise NotImplementedError

    class Output:
        @Signal
        def on_board_output(self, xml_data:bytes) -> None:
            raise NotImplementedError


class BoardRenderer(Component, LXBoard,
                    LXSystem.Layout, LXSystem.Rules, LXSystem.Board,
                    COREApp.Start):
    """ Creates graphics, captions, and example links for the board diagram. """

    _generator: BoardGenerator = None
    _key_matcher: KeyMatcher = None
    _rule_matcher: RuleMatcher = None

    def on_app_start(self) -> None:
        """ Parse the board XML into individual steno key/rule elements. """
        defs = json.loads(self.engine_call(SYSFile.read, _DEFS_ASSET_PATH, ignore_missing=True))
        xml_dict = XMLElementDict(defs)
        xml_dict.add_recursive(self.board)
        self._make_generator(xml_dict[_BASE_TAG], defs[_BOUNDS_DEF])
        self._make_key_matcher(xml_dict[_SINGLE_TAG], xml_dict[_UNMATCHED_TAG])
        self._make_rule_matcher(xml_dict[_RULE_TAG])

    def _make_generator(self, base:dict, bounds:list) -> None:
        base_elements = list(base.values())
        self._generator = BoardGenerator(base_elements, bounds)

    def _make_key_matcher(self, keys:dict, unmatched:dict) -> None:
        layout = self.layout
        sep = layout.SEP
        keys[sep] = unmatched[sep] = STROKE_SENTINEL
        self._key_matcher = KeyMatcher(layout.from_rtfcre, keys, unmatched)

    def _make_rule_matcher(self, elements:dict) -> None:
        rules = self.rules
        rule_dict = {rules[k]: elements[k] for k in elements if k in rules}
        self._rule_matcher = RuleMatcher(self._key_matcher, rule_dict)

    def from_keys(self, keys:str, ratio:float=_DEFAULT_RATIO) -> bytes:
        if self._generator is None:
            return b""
        elems = self._key_matcher(keys)
        return self._generate(elems, ratio)

    def from_rule(self, rule:StenoRule, ratio:float=_DEFAULT_RATIO, *, show_compound:bool=True) -> bytes:
        if self._generator is None:
            return b""
        elems = self._rule_matcher(rule) if show_compound else self._key_matcher(rule.keys)
        return self._generate(elems, ratio)

    def _generate(self, elems, ratio:float) -> bytes:
        xml_data = self._generator(elems, ratio)
        self.engine_call(self.Output, xml_data)
        return xml_data
