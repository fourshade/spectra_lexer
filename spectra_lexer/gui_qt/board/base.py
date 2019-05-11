from typing import List

from PyQt5.QtGui import QPicture

from .renderer import BoardSVGRenderer
from spectra_lexer.gui import BoardDisplay
from spectra_lexer.types import delegate_to


class GUIQtBoardDisplay(BoardDisplay):
    """ Draws steno board diagram elements and the description for rules. """

    w_desc = resource("gui:w_display_desc")    # Displays rule description.
    w_board = resource("gui:w_display_board")  # Displays steno board diagram.

    _renderer: BoardSVGRenderer = None  # Main renderer of SVG steno board graphics.

    @on("gui_load")
    def load(self) -> None:
        """ Create the renderer, connect the signals, and initialize the board size. """
        self._renderer = BoardSVGRenderer()
        self.w_board.onActivateLink.connect(self.on_link)
        self.w_board.onResize.connect(self.on_resize)
        self.w_board.resizeEvent()

    def set_caption(self, caption:str) -> None:
        self.w_desc.setText(caption)

    def set_layout(self, element_info:List[tuple]) -> None:
        """ Draw new elements with the renderer and send the finished picture to the board. """
        gfx = QPicture()
        self._renderer.draw(gfx, element_info)
        self.w_board.set_gfx(gfx)

    set_xml = delegate_to("_renderer.load")
    set_link_enabled = delegate_to("w_board")
