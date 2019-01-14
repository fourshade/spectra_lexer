""" Module for generating steno board diagram elements. No state is required to be maintained. """

from typing import List, Tuple

from spectra_lexer.output.node import OutputNode

# Parameters for creating SVG element IDs from steno characters.
SVG_BASE_ID = "Base"
SVG_ORD_FORMAT = "_x{:X}_"
SVG_ALT_PREFIX = "Alt"


def make_board_info(node:OutputNode) -> Tuple[List[List[str]], str]:
    """ Generate board diagram elements from steno keys and send them along with the description. """
    elements = [_get_stroke_ids(s, alt) for (s, alt) in node.raw_keys.for_display()]
    return elements, node.description


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
