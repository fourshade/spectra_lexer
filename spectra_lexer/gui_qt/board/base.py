from typing import List

from PyQt5.QtWidgets import QLineEdit, QWidget

from spectra_lexer import on, SpectraComponent
from spectra_lexer.keys import StenoKeys, split_strokes, is_number
from spectra_lexer.node import OutputNode
from spectra_lexer.gui_qt.board.steno_board_widget import StenoBoardWidget

# Parameters for creating SVG element IDs from steno characters.
SVG_PARAMS = {"base_id":       "Base",
              "ord_format":    "_x{:X}_",
              "number_prefix": "Alt"}


class GUIQtBoardDisplay(SpectraComponent):
    """ Generates steno board diagram elements for a given node,
        including graphical element IDs and the description. """

    w_desc: QLineEdit          # Displays rule description.
    w_board: StenoBoardWidget  # Displays steno board diagram.

    def __init__(self, *widgets:QWidget):
        super().__init__()
        self.w_desc, self.w_board = widgets

    @on("new_output_tree")
    def make_board(self, node:OutputNode) -> None:
        """ Generate a steno board diagram and info for a steno rule and display it. """
        elements = _get_svg_ids(node.raw_keys, **SVG_PARAMS)
        desc = node.description
        self.w_board.set_elements(elements)
        self.w_desc.setText(desc)

    # Currently, only one <on> decorator can attach to a method at once.
    @on("new_output_selected")
    def make_board2(self, node:OutputNode) -> None:
        self.make_board(node)

    # TODO: Process mouseover on diagram keys
    # def process_mouseover(self, x:int, y:int) -> Optional[OutputNode]:
    #     if node is None or node is self._last_node:
    #         return None
    #     return node


def _get_svg_ids(keys:StenoKeys, **params) -> List[List[str]]:
    """ Make a list of SVG element id lists, each of which makes up a steno board diagram.
        A full diagram is drawn for each stroke in a given steno key string. """
    return [_get_key_ids(s, **params) for s in split_strokes(keys)]


def _get_key_ids(stroke:str, base_id:str, ord_format:str, number_prefix:str) -> List[str]:
    """ Returns a list of SVG element IDs for each key in a lexer-formatted stroke in order.
        The gray base board with <base_id> is always drawn first, on the bottom layer.
        Any character that isn't a letter is represented by its ordinal in its element ID,
        which is formatted according to <ord_format> using standard string format notation.
        If there's a number key, add alternate number-based elements on top of each active key.
        Each one has the same ID as its corresponding letter, prefixed by <number_prefix>. """
    elements = [k if k.isalpha() else ord_format.format(ord(k)) for k in stroke]
    if is_number(stroke):
        elements += [number_prefix + k for k in elements]
    return [base_id] + elements
