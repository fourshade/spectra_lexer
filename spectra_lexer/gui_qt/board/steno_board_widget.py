from typing import Dict, Iterable, List

from PyQt5.QtCore import QRectF, QXmlStreamReader
from PyQt5.QtGui import QPainter, QPaintEvent
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import QWidget


class StenoBoardWidget(QWidget):
    """ Widget to display all the keys that make up a steno stroke pictorally. """

    _gfx_board: QSvgRenderer            # Main renderer of SVG steno board graphics.
    _draw_list: List[tuple] = []        # List of graphical element IDs with bounds rects.
    _bounds: Dict[str, tuple] = {}      # (x, y, w, h) bounds of each graphical element by id.

    def __init__(self, *args):
        super().__init__(*args)
        self._gfx_board = QSvgRenderer()

    def set_update_callback(self, cb:callable) -> None:
        """ Set a callback to receive new properties for the board widget on any size change. """
        def set_layout(*args) -> None:
            cb(self._gfx_board.viewBox().getRect(), self.width(), self.height())
        self.resizeEvent = set_layout

    def load(self, xml_text:str, ids:Iterable[str]) -> None:
        """ Load the board graphics from an SVG XML string. Send a resize event at the end to update the main component.
            Compute and store a dict of bounds for all given element IDs, as well as the top-level viewbox. """
        self._gfx_board.load(QXmlStreamReader(xml_text))
        self._bounds = {k: self._gfx_board.boundsOnElement(k).getRect() for k in ids}
        self.resizeEvent()

    def set_elements(self, gfx:Iterable[tuple]) -> None:
        """ Set the current list of element ids and bound rects and draw the new elements. """
        self._draw_list = []
        bounds = self._bounds
        for (el, ox, oy, scale) in gfx:
            if el in bounds:
                x, y, w, h = [c * scale for c in bounds[el]]
                rectf = QRectF(x + ox, y + oy, w, h)
                self._draw_list.append((el, rectf))
        self.update()

    def paintEvent(self, event:QPaintEvent) -> None:
        """ Display the current steno key set on the board diagram when GUI repaint occurs.
            Undefined elements are simply ignored. """
        p = QPainter(self)
        render = self._gfx_board.render
        for (el, rectf) in self._draw_list:
            render(p, el, rectf)
