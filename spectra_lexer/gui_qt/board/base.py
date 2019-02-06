from typing import List

from PyQt5.QtWidgets import QLineEdit, QWidget

from spectra_lexer import Component, on
from spectra_lexer.gui_qt.board.steno_board_widget import StenoBoardWidget


class GUIQtBoardDisplay(Component):
    """ Generates steno board diagram elements for a given node,
        including graphical element IDs and the description. """

    ROLE = "gui_board"

    w_desc: QLineEdit          # Displays rule description.
    w_board: StenoBoardWidget  # Displays steno board diagram.

    def __init__(self, *widgets:QWidget):
        super().__init__()
        self.w_desc, self.w_board = widgets

    @on("new_board")
    def set_gfx(self, xml_dict:dict) -> None:
        """ Load the board graphics from the raw characters of an SVG XML file. """
        self.w_board.load(xml_dict["raw"])

    @on("new_board_info")
    def display_board(self, elements:List[List[str]], description:str) -> None:
        """ Generate steno board diagram elements and display them along with the rule description. """
        self.w_board.set_elements(elements)
        self.w_desc.setText(description)

    # TODO: Process mouseover on diagram keys
    # def process_mouseover(self, x:int, y:int):
    #     if node is None or node is self._last_node:
    #         return None
    #     return node
