from typing import List

from PyQt5.QtGui import QPainter, QPaintEvent
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import QWidget

BOARD_GFX = ':/spectra_lexer/board.svg'


class StenoBoardWidget(QWidget):
    """ Widget to display all the keys that make up a steno stroke pictorally. """

    _gfx_board: QSvgRenderer  # Painter of base steno board graphic.
    _stroke_list: List[str]   # Current list of graphical stroke elements.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._gfx_board = QSvgRenderer(BOARD_GFX)
        self._stroke_list = []

    def paintEvent(self, event:QPaintEvent) -> None:
        """ Display the currently stored rule description and steno key set.
            For each stroke, the gray base board is always drawn first, on the bottom layer.
            The active keys are drawn on top of it. With one stroke only, it fills the whole box.
            With multiple strokes (max 4), each copy of the board occupies a quarter of the box. """
        p = QPainter(self)
        g = self._gfx_board
        if len(self._stroke_list) == 1:
            for k in ("Base", *self._stroke_list[0]):
                g.render(p, k, g.boundsOnElement(k))
        else:
            offset_step_x = self.width() / 2
            offset_step_y = self.height() / 2
            for i, s in enumerate(self._stroke_list[:4]):
                for k in ("Base", *s):
                    bounds = g.boundsOnElement(k)
                    x, y, width, height = [c / 2 for c in bounds.getRect()]
                    x += offset_step_x * (i % 2)
                    y += offset_step_y * (i // 2)
                    bounds.setCoords(x, y, x + width, y + height)
                    g.render(p, k, bounds)

    def show_keys(self, keys:str) -> None:
        """ Record the keys of each stroke and description used in the current rule, then display them.
            Any character that isn't a letter is represented by its ordinal in its SVG element ID.
            If there's a number key, display the number-based elements that exist on top. """
        self._stroke_list = []
        numerals = "#" in keys
        for s in keys.split("/"):
            stroke = []
            for k in s:
                if k.isalpha():
                    stroke.append(k)
                    if numerals:
                        stroke.append("Alt" + k)
                else:
                    stroke.append("_x{:X}_".format(ord(k)))
            self._stroke_list.append(stroke)
        self.update()
