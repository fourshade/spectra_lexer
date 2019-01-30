""" Module for generating steno board diagram elements. """

from typing import List, Tuple

from spectra_lexer import Component, pipe
from spectra_lexer.rules import RuleFlags, StenoRule

# Parameters for creating SVG element IDs from steno characters.
SVG_BASE_ID = "Base"
SVG_ORD_FORMAT = "_x{:X}_"
SVG_ALT_PREFIX = "Alt"


class BoardRenderer(Component):
    """ Creates graphics and description strings for the board diagram. """

    ROLE = "board"

    @pipe("new_lexer_result", "new_board_info", unpack=True)
    def make_board_from_rule(self, rule:StenoRule) -> Tuple[List[List[str]], str]:
        """ Generate board diagram elements from a steno rule and send them along with the description. """
        keys, letters, flags, desc, rulemap = rule
        raw_keys = keys.to_rtfcre()
        if RuleFlags.GENERATED in flags:
            # If this is a lexer-generated rule (usually the root at the top), just display the description.
            description = desc
        elif not rulemap:
            # Base rules (i.e. leaf nodes) display their keys to the left of their descriptions.
            description = "{}: {}".format(raw_keys, desc)
        else:
            # Derived rules (i.e. non-leaf nodes) show the complete mapping of keys to letters in their description.
            description = "{} → {}: {}".format(raw_keys, letters, desc)
        elements = [_get_stroke_ids(s, alt) for (s, alt) in keys.for_display()]
        return elements, description

    @pipe("new_graph_selection", "new_board_info", unpack=True)
    def make_board_from_node(self, rule:StenoRule) -> Tuple[List[List[str]], str]:
        """ The task is identical whether the rule is from a new lexer result or a user graph selection. """
        return self.make_board_from_rule(rule)


def _get_stroke_ids(stroke:str, alt_mode:bool) -> List[str]:
    """ Return a list of SVG element IDs for each key in a lexer-formatted stroke in order.
        The gray base board with <base_id> is always drawn first, on the bottom layer.
        Any character that isn't a letter is represented by its ordinal in its element ID,
        which is formatted according to <ord_format> using standard string format notation.
        Alt-mode means there's a number key. Add alternate number-based elements on top of each active key.
        Each one has the same ID as its corresponding letter, prefixed by <alt_prefix>. """
    elements = [SVG_BASE_ID]
    elements += [k if k.isalpha() else SVG_ORD_FORMAT.format(ord(k)) for k in stroke]
    if alt_mode:
        elements += [SVG_ALT_PREFIX + k for k in elements]
    return elements
