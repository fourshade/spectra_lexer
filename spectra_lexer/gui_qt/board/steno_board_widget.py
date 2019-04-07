from typing import Callable, Iterable

from PyQt5.QtGui import QPaintEvent
from PyQt5.QtWidgets import QWidget

from spectra_lexer.gui_qt.svg import LayoutRenderer


class StenoBoardWidget(QWidget):
    """ Widget to display all the keys that make up a steno stroke pictorally. """

    _gfx_board: LayoutRenderer                   # Main renderer of SVG steno board graphics.
    resize_callback: Callable[..., None] = None  # Callback to send board size changes to the main component.

    def __init__(self, *args):
        super().__init__(*args)
        self._gfx_board = LayoutRenderer()

    def set_xml(self, xml_text:str, ids:Iterable[str]) -> None:
        """ Load the board graphics and send a resize event to update the main component. """
        self._gfx_board.load_str(xml_text)
        self._gfx_board.load_ids(ids)
        self.resizeEvent()

    def set_layout(self, element_info:Iterable[tuple]) -> None:
        """ Update the draw list with the new elements and immediately repaint the board. """
        self._gfx_board.set_elements(element_info)
        self.update()

    def paintEvent(self, event:QPaintEvent) -> None:
        """ Display the current steno key set on the board diagram when GUI repaint occurs. """
        self._gfx_board.paint(self)

    def resizeEvent(self, *args) -> None:
        """ Send new properties of the board widget on any size change. """
        if self.resize_callback is not None:
            self.resize_callback(self._gfx_board.viewbox_tuple(), self.width(), self.height())
