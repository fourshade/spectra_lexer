from typing import Iterable

from PyQt5.QtWidgets import QLineEdit, QWidget

from spectra_lexer import Component, on
from spectra_lexer.gui_qt.board.steno_board_widget import StenoBoardWidget


class GUIQtBoardDisplay(Component):
    """ Draws steno board diagram elements and the description for rules. """

    ROLE = "gui_board"

    w_desc: QLineEdit          # Displays rule description.
    w_board: StenoBoardWidget  # Displays steno board diagram.

    def __init__(self, *widgets:QWidget):
        super().__init__()
        self.w_desc, self.w_board = widgets
        self.w_board.set_update_callback(self.set_layout)

    def set_layout(self, *args) -> None:
        """ Send the bounds of graphical elements, the view box, and the size of the board to the main component. """
        self.engine_call("board_set_layout", *args)

    @on("new_board_setup")
    def set_gfx(self, xml_text:str, ids:Iterable[str]) -> None:
        """ Load the board graphics from the raw characters of an SVG XML file. """
        self.w_board.load(xml_text, ids)

    @on("new_board_gfx")
    def display_gfx(self, board_gfx:Iterable[tuple]) -> None:
        """ Draw the given set of board elements. """
        self.w_board.set_elements(board_gfx)

    @on("new_board_description")
    def display_desc(self, description:str) -> None:
        """ Draw the rule description. """
        self.w_desc.setText(description)
