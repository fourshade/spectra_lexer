from functools import partial

from PyQt5.QtWidgets import QLineEdit, QWidget

from .steno_board_widget import StenoBoardWidget
from spectra_lexer import Component
from spectra_lexer.utils import delegate_to


class GUIQtBoardDisplay(Component):
    """ Draws steno board diagram elements and the description for rules. """

    w_desc: QLineEdit          # Displays rule description.
    w_board: StenoBoardWidget  # Displays steno board diagram.

    @on("new_gui_board")
    def new_gui(self, *widgets:QWidget) -> None:
        """ Save the required widgets and set the size change callback. """
        self.w_desc, self.w_board = widgets
        # Send the SVG view box and the size of the board on resize.
        self.w_board.resize_callback = partial(self.engine_call, "board_set_view")

    set_description = on("new_board_description")(delegate_to("w_desc.setText"))

    set_xml = on("new_board_xml")(delegate_to("w_board"))
    set_layout = on("new_board_layout")(delegate_to("w_board"))
