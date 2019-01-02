from math import ceil, sqrt
from typing import List

from PyQt5.QtGui import QPainter, QPaintEvent
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import QWidget

# Qt resource identifier for the main SVG graphic (containing every element needed).
BOARD_GFX:str = ':/spectra_lexer/board.svg'


class StenoBoardWidget(QWidget):
    """ Widget to display all the keys that make up a steno stroke pictorally. """

    _gfx_board: QSvgRenderer  # Painter of base steno board graphic.
    _draw_list: List[tuple]   # Current list of graphical elements with bounds.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._gfx_board = QSvgRenderer(BOARD_GFX)
        self._draw_list = []

    def set_elements(self, elements:List[List[str]]) -> None:
        """ Compute the drawing bounds for the keys of each stroke, then
            display them on the board diagram by requesting a repaint. """
        assert elements
        self.make_draw_list(elements)
        self.update()

    def make_draw_list(self, elements:List[List[str]]) -> None:
        """ Calculate the bounds of each key on the board diagram.
            With one stroke only, the diagram fills the entire bounds box.
            With multiple strokes, each diagram is tiled in a grid layout. """
        self._draw_list = []
        get_bounds = self._gfx_board.boundsOnElement
        n = ceil(sqrt(len(elements)))
        if n == 1:
            # Skip the divisions for a single stroke (looks cleaner).
            self._draw_list = [(k, get_bounds(k)) for k in elements[0]]
            return
        offset_step_x = self.width() / n
        offset_step_y = self.height() / n
        for i, stroke in enumerate(elements):
            steps_y, steps_x = divmod(i, n)
            for k in stroke:
                bounds = get_bounds(k)
                x, y, width, height = [c / n for c in bounds.getRect()]
                x += offset_step_x * steps_x
                y += offset_step_y * steps_y
                bounds.setCoords(x, y, x + width, y + height)
                self._draw_list.append((k, bounds))

    def paintEvent(self, event:QPaintEvent) -> None:
        """ Display the current steno key set on the board diagram when GUI repaint occurs. """
        p = QPainter(self)
        g = self._gfx_board
        for (el, bounds) in self._draw_list:
            g.render(p, el, bounds)
