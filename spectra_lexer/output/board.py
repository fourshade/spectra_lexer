""" Module for generating steno board diagram elements. """

from typing import List, Tuple

from spectra_lexer import Component, pipe
from spectra_lexer.output.node import OutputNode

# Parameters for creating SVG element IDs from steno characters.
SVG_BASE_ID = "Base"
SVG_ORD_FORMAT = "_x{:X}_"
SVG_ALT_PREFIX = "Alt"


class BoardDiagram(Component):
    """ Creates graphics and description strings for the board diagram. """

    ROLE = "output_board"

    @pipe("new_output_tree", "new_output_board", unpack=True)
    def make_board_info(self, node:OutputNode) -> Tuple[List[List[str]], str]:
        """ Generate board diagram elements from steno keys and send them along with the description. """
        elements = [self._get_stroke_ids(s, alt) for (s, alt) in node.raw_keys.for_display()]
        return elements, node.description

    @pipe("new_output_selection", "new_output_board", unpack=True)
    def make_selected_info(self, node:OutputNode) -> Tuple[List[List[str]], str]:
        """ The task is identical whether the node is from a new graph or not. """
        return self.make_board_info(node)

    def _get_stroke_ids(self, stroke:str, alt_mode:bool) -> List[str]:
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
