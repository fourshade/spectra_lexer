from html import escape, unescape
from typing import List

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QPainter, QPicture
from PyQt5.QtWidgets import QLabel, QWidget

from .renderer import BoardSVGRenderer
from spectra_lexer.types import delegate_to


class StenoBoardWidget(QWidget):
    """ Widget to display all the keys that make up a steno stroke pictorally. """

    _renderer: BoardSVGRenderer  # Main renderer of SVG steno board graphics.
    _w_link: QLabel              # Displays rule hyperlink.
    _gfx: QPicture = QPicture()  # Last recorded rendering of the steno board.

    def __init__(self, *args):
        super().__init__(*args)
        self._renderer = BoardSVGRenderer()
        self._w_link = QLabel(self)
        self._w_link.setVisible(False)
        self._w_link.linkActivated.connect(lambda s: self.onActivateLink.emit(unescape(s)))

    set_xml = delegate_to("_renderer.load")

    def set_link(self, link_ref:str) -> None:
        """ Show a link in the bottom-right corner of the diagram if examples exist. """
        self._w_link.setText(f"<a href='{escape(link_ref)}'>More Examples</a>")
        self._w_link.setVisible(bool(link_ref))

    def set_layout(self, element_info:List[tuple]) -> None:
        """ Draw new elements with the renderer and immediately repaint the board. """
        self._gfx = QPicture()
        self._renderer.draw(self._gfx, element_info)
        self.update()

    def paintEvent(self, *args) -> None:
        """ Paint the current set of elements on this widget when GUI repaint occurs. """
        self._gfx.play(QPainter(self))

    def resizeEvent(self, *args) -> None:
        """ Reposition the link and send the new widget dimensions on any size change. """
        self._w_link.move(self.width() - 75, self.height() - 18)
        self.onResize.emit(self.width(), self.height())

    # Signals
    onActivateLink = pyqtSignal([str])
    onResize = pyqtSignal([int, int])
