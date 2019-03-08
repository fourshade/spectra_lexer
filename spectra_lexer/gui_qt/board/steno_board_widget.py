from typing import Dict, List, Tuple

from PyQt5.QtCore import QRectF, QXmlStreamReader
from PyQt5.QtGui import QPainter, QPaintEvent
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import QWidget


class StenoBoardWidget(QWidget):
    """ Widget to display all the keys that make up a steno stroke pictorally. """

    _gfx_board: QSvgRenderer            # Painter of base steno board graphic.
    _draw_list: List[tuple] = []        # (el, x, y, w, h) graphical elements with bounds.
    _bounds: Dict[str, tuple] = {}      # (x, y, w, h) bounds of each graphical element by id.
    _viewbox: tuple = (0, 0, 100, 100)  # (x, y, w, h) bounds of the SVG view box for the root element.

    def __init__(self, *args):
        super().__init__(*args)
        self._gfx_board = QSvgRenderer()

    def set_update_callback(self, cb:callable) -> None:
        """ Set a callback to receive new properties for the board widget on any size change. """
        def set_layout(*args) -> None:
            cb(self._bounds, self._viewbox, self.width(), self.height())
        self.resizeEvent = set_layout

    def load(self, xml_text:str, ids:List[str]) -> None:
        """ Load the board graphics from an SVG XML string. Send a resize event at the end to update the main component.
            Compute and store a dict of bounds for all given element IDs, as well as the top-level viewbox. """
        self._gfx_board.load(QXmlStreamReader(xml_text))
        self._bounds = {k: self._gfx_board.boundsOnElement(k).getRect() for k in ids}
        self._viewbox = self._gfx_board.viewBox().getRect()
        self.resizeEvent()

    def set_elements(self, gfx:List[tuple]) -> None:
        """ Set the current list of element ids and bounds and draw the new elements. """
        self._draw_list = gfx
        self.update()

    def paintEvent(self, event:QPaintEvent) -> None:
        """ Display the current steno key set on the board diagram when GUI repaint occurs.
            Undefined elements are simply ignored. """
        p = QPainter(self)
        render = self._gfx_board.render
        for (el, x, y, w, h) in self._draw_list:
            render(p, el, QRectF(x, y, w, h))
