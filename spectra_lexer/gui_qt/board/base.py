from functools import partial

from spectra_lexer import Component
from spectra_lexer.utils import delegate_to


class GUIQtBoardDisplay(Component):
    """ Draws steno board diagram elements and the description for rules. """

    w_desc = resource("gui:w_display_desc", desc="Displays rule description.")
    w_board = resource("gui:w_display_board", desc="Displays steno board diagram.")

    @on("load_gui")
    def load(self) -> None:
        """ Connect the signal to get the size of the board widget on resize. """
        self.w_board.onActivateLink.connect(partial(self.engine_call, "board_find_examples"))
        self.w_board.onResize.connect(partial(self.engine_call, "board_set_size"))

    set_xml = on("new_board_xml")(delegate_to("w_board"))
    set_layout = on("new_board_layout")(delegate_to("w_board"))

    @on("new_board_caption")
    def set_caption(self, caption:str, link_ref:str="") -> None:
        """ Show a caption above the board and optionally a link in the bottom-right corner. """
        self.w_desc.setText(caption)
        self.w_board.set_link(link_ref)
