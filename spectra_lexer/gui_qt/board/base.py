from html import escape, unescape

from PyQt5.QtWidgets import QLabel

from spectra_lexer import Component
from spectra_lexer.utils import delegate_to


class GUIQtBoardDisplay(Component):
    """ Draws steno board diagram elements and the description for rules. """

    w_desc = Resource("gui",  "w_display_desc",  None, "Displays rule description.")
    w_board = Resource("gui", "w_display_board", None, "Displays steno board diagram.")

    w_link: QLabel = None   # Displays rule hyperlink. Created dynamically.

    @on("load_gui")
    def load(self) -> None:
        """ Set hyperlinks to search examples when clicked. """
        self.w_link = QLabel(self.w_board)
        self.w_link.setVisible(False)
        self.w_link.linkActivated.connect(lambda s: self.engine_call("board_find_examples", unescape(s)))
        # Connect the signal to get the sizes of the SVG view box and board widget on resize.
        self.w_board.onResize.connect(self.on_resize)

    @on("new_board_caption")
    def set_link(self, caption:str, link_ref:str= "") -> None:
        """ Show a caption above the board and optionally a link in the bottom-right corner. """
        self.w_desc.setText(caption)
        # Set reference to show examples of the displayed rule if examples exist.
        self.w_link.setText(f"<a href='{escape(link_ref)}'>More Examples</a>")
        self.w_link.setVisible(bool(link_ref))

    set_xml = on("new_board_xml")(delegate_to("w_board"))
    set_layout = on("new_board_layout")(delegate_to("w_board"))

    def on_resize(self, view_box:tuple, width:int, height:int) -> None:
        """ Reposition the link and send new properties of the board widget on any size change. """
        self.w_link.move(width - 75, height - 18)
        self.engine_call("board_set_view", view_box, width, height)
