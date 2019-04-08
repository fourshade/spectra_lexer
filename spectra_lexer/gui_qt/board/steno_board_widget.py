from typing import List, Tuple

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QPainter, QTransform
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import QWidget


class StenoBoardWidget(QWidget):
    """ Widget to display all the keys that make up a steno stroke pictorally. """

    _renderer: QSvgRenderer       # Main renderer of SVG steno board graphics.
    _draw_list: List[tuple] = []  # List of strokes, each with a transform and graphical element IDs with bounds.

    def __init__(self, *args):
        super().__init__(*args)
        self._renderer = QSvgRenderer()

    def set_xml(self, *args) -> None:
        """ Load the board graphics and send a resize event to update the main component. """
        self._renderer.load(*args)
        self.resizeEvent()

    def set_layout(self, scale:float, element_info:List[Tuple[float, float, list]]) -> None:
        """ Load the draw list with new elements and bounds, including transforms for scaling and offsetting. """
        self._draw_list = [(QTransform(scale, 0, 0, scale, ox, oy),
                            [(e_id, self._renderer.boundsOnElement(e_id)) for e_id in stroke])
                           for (ox, oy, stroke) in element_info]
        # Immediately repaint the board.
        self.update()

    def paintEvent(self, *args) -> None:
        """ Display the current steno key set on the board diagram when GUI repaint occurs. """
        with QPainter(self) as p:
            for trfm, stroke in self._draw_list:
                p.setTransform(trfm)
                for e_id, bounds in stroke:
                    self._renderer.render(p, e_id, bounds)

    def resizeEvent(self, *args) -> None:
        """ Send new properties of the board widget on any size change. """
        self.onResize.emit(self._renderer.viewBox().getRect(), self.width(), self.height())

    # Signals
    onResize = pyqtSignal([tuple, int, int])
