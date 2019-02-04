from typing import List

from PyQt5.QtWidgets import QLineEdit, QWidget

from spectra_lexer import Component, on
from spectra_lexer.gui_qt.board.layout import ElementLayout
from spectra_lexer.gui_qt.board.steno_board_widget import StenoBoardWidget


class GUIQtBoardDisplay(Component):
    """ Generates steno board diagram elements for a given node,
        including graphical element IDs and the description. """

    ROLE = "gui_board"

    w_desc: QLineEdit              # Displays rule description.
    w_board: StenoBoardWidget      # Displays steno board diagram.
    _layout: ElementLayout = None  # Gets bounds for each element.
    _elements: List[List[str]]     # Current list of graphical element names for each stroke.
    _width: int = 100              # Total width of the diagram widget in pixels.
    _height: int = 100             # Total height of the diagram widget in pixels.

    def __init__(self, *widgets:QWidget):
        super().__init__()
        self._elements = []
        self.w_desc, self.w_board = widgets
        self.w_board.resizeEvent = self.set_size

    @on("new_board_setup")
    def set_gfx(self, xml_text:str, ids:List[str]) -> None:
        """ Load the board graphics from the raw characters of an SVG XML file.
            Save the bounds of all graphical elements and the view box ahead of time. """
        self._layout = ElementLayout(*self.w_board.load(xml_text, ids))

    @on("new_board_info")
    def display_board(self, elements:List[List[str]], description:str) -> None:
        """ Generate steno board diagram elements and display them along with the rule description. """
        self.w_desc.setText(description)
        self._elements = elements
        self._draw_board()

    def set_size(self, *args) -> None:
        """ Set the layout's max bounds to be the new size of the board widget and redraw it. """
        self._width = self.w_board.width()
        self._height = self.w_board.height()
        self._draw_board()

    def _draw_board(self):
        """ Draw the current set of board elements if the graphics are loaded. """
        if self._layout is not None:
            gfx = self._layout.generate(self._elements, self._width, self._height)
            self.w_board.set_elements(gfx)
