from typing import List, Tuple

from PyQt5.QtWidgets import QLineEdit, QWidget

from spectra_lexer import on, SpectraComponent
from spectra_lexer.gui_qt.board.steno_board_widget import StenoBoardWidget

# Parameters for creating SVG element IDs from steno characters.
SVG_BASE_ID = "Base"
SVG_ORD_FORMAT = "_x{:X}_"
SVG_ALT_PREFIX = "Alt"


class GUIQtBoardDisplay(SpectraComponent):
    """ Generates steno board diagram elements for a given node,
        including graphical element IDs and the description. """

    w_desc: QLineEdit          # Displays rule description.
    w_board: StenoBoardWidget  # Displays steno board diagram.

    def __init__(self, *widgets:QWidget):
        super().__init__()
        self.w_desc, self.w_board = widgets

    @on("new_output_info")
    def make_board(self, strokes:List[Tuple[str, bool]], description:str) -> None:
        """ Generate steno board diagram elements and display them along with the rule description. """
        elements = [_get_element_ids(s, alt) for (s, alt) in strokes]
        self.w_board.set_elements(elements)
        self.w_desc.setText(description)

    # TODO: Process mouseover on diagram keys
    # def process_mouseover(self, x:int, y:int):
    #     if node is None or node is self._last_node:
    #         return None
    #     return node


def _get_element_ids(stroke:str, alt_mode:bool) -> List[str]:
    """ Returns a list of SVG element IDs for each key in a lexer-formatted stroke in order.
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
