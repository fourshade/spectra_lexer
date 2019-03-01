from functools import partial
from typing import Dict, Iterable

from PyQt5.QtWidgets import QLineEdit, QWidget

from spectra_lexer import Component, on
from spectra_lexer.gui_qt.board.steno_board_widget import StenoBoardWidget


class GUIQtBoardDisplay(Component):
    """ Draws steno board diagram elements and the description for rules. """

    ROLE = "gui_board"

    w_desc: QLineEdit          # Displays rule description.
    w_board: StenoBoardWidget  # Displays steno board diagram.

    @on("new_gui_window")
    def start(self, widgets:Dict[str, QWidget]) -> None:
        """ Get the required widgets and set the size change callback. """
        self.w_desc, self.w_board = widgets["board"]
        # Send the bounds of graphical elements, the view box, and the size of the board on resize.
        self.w_board.resize_callback = partial(self.engine_call, "board_set_layout")

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
