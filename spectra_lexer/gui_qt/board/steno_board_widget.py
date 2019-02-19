from typing import Dict, List, Tuple

from PyQt5.QtCore import QRectF, QXmlStreamReader
from PyQt5.QtGui import QPainter, QPaintEvent
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import QWidget


class StenoBoardWidget(QWidget):
    """ Widget to display all the keys that make up a steno stroke pictorally. """

    _gfx_board: QSvgRenderer      # Painter of base steno board graphic.
    _draw_list: List[tuple]       # (el, x, y, w, h) graphical elements with bounds.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._gfx_board = QSvgRenderer()
        self._draw_list = []

    def load(self, xml:str, ids:List[str]) -> Tuple[Dict[str, tuple], tuple]:
        """ Load the board graphics from an SVG XML string. Return a dict of bounds for all relevant elements. """
        g = self._gfx_board
        g.load(QXmlStreamReader(xml))
        return {k: g.boundsOnElement(k).getRect() for k in ids}, g.viewBox().getRect()

    def set_elements(self, gfx:List[tuple]) -> None:
        """ Set the current list of element ids and bounds and draw the new elements. """
        self._draw_list = gfx
        self.update()

    def paintEvent(self, event:QPaintEvent) -> None:
        """ Display the current steno key set on the board diagram when GUI repaint occurs. """
        p = QPainter(self)
        render = self._gfx_board.render
        for (el, x, y, w, h) in self._draw_list:
            render(p, el, QRectF(x, y, w, h))
