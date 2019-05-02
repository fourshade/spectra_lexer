from spectra_lexer.gui import BoardDisplay
from spectra_lexer.utils import delegate_to


class GUIQtBoardDisplay(BoardDisplay):
    """ Draws steno board diagram elements and the description for rules. """

    w_desc = resource("gui:w_display_desc", desc="Displays rule description.")
    w_board = resource("gui:w_display_board", desc="Displays steno board diagram.")

    def load(self) -> None:
        self.w_board.onActivateLink.connect(self.on_link)
        self.w_board.onResize.connect(self.on_resize)

    def set_caption(self, caption:str, link_ref:str="") -> None:
        self.w_desc.setText(caption)
        self.w_board.set_link(link_ref)

    set_xml = delegate_to("w_board")
    set_layout = delegate_to("w_board")
