from functools import partial

from PyQt5.QtWidgets import QLabel, QWidget

from .steno_board_widget import StenoBoardWidget
from spectra_lexer import Component
from spectra_lexer.utils import delegate_to

# Delimiter for storing multiple strings in a hyperlink anchor.
_LINK_DELIM = "|"


class GUIQtBoardDisplay(Component):
    """ Draws steno board diagram elements and the description for rules. """

    w_desc: QLabel             # Displays rule description.
    w_board: StenoBoardWidget  # Displays steno board diagram.

    @on("new_gui_board")
    def new_gui(self, *widgets:QWidget) -> None:
        """ Save the required widgets and set the size change callback. """
        self.w_desc, self.w_board = widgets
        # Set description label hyperlinks to search examples when clicked.
        self.w_desc.linkActivated.connect(lambda s: self.engine_call("search_examples", *s.split(_LINK_DELIM)))
        # Send the SVG view box and the size of the board on resize.
        self.w_board.resize_callback = partial(self.engine_call, "board_set_view")

    set_caption = on("new_board_caption")(delegate_to("w_desc.setText"))

    @on("new_board_link")
    def set_link(self, params:tuple) -> None:
        """ Add an HTML hyperlink to show examples of the displayed rule. """
        text = self.w_desc.text()
        if params:
            ref = _LINK_DELIM.join(params)
            text += f" <a href='{ref}'>More Examples</a>"
        self.w_desc.setText(text)

    set_xml = on("new_board_xml")(delegate_to("w_board"))
    set_layout = on("new_board_layout")(delegate_to("w_board"))
