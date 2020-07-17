from math import ceil
from typing import Tuple

from . import Offset, OffsetSequence


class GridLayoutEngine:
    """ Calculates dimensions and offsets for items arranged in a grid. """

    def __init__(self, left:int, top:int, width:int, height:int) -> None:
        self._left = left      # X offset for the full grid.
        self._top = top        # Y offset for the full grid.
        self._width = width    # Width of a single cell.
        self._height = height  # Height of a single cell.

    def column_count(self, count:int, aspect_ratio:float) -> int:
        """ Calculate the number of columns for an arrangement of <count> cells
            with the best possible scale in a viewing area of <aspect_ratio>. """
        diagram_ratio = self._width / self._height
        # rel_ratio is the aspect ratio of one cell divided by that of the viewing area.
        rel_ratio = diagram_ratio / aspect_ratio
        r = min(rel_ratio, 1 / rel_ratio)
        s = int((count * r) ** 0.5) or 1
        if r * ceil(count / s) > (s + 1):
            s += 1
        return ceil(count / s) if rel_ratio < 1 else s

    def _get_offset(self, i:int, ncols:int) -> Offset:
        """ Return a (dx, dy) offset for row-major cell <i> in a grid with <ncols> columns. """
        dx = self._width * (i % ncols)
        dy = self._height * (i // ncols)
        return dx, dy

    def offsets(self, count:int, ncols:int) -> OffsetSequence:
        """ Return evenly spaced offsets for a grid with <count> cells in <ncols> columns. """
        return [self._get_offset(i, ncols) for i in range(count)]

    def viewbox(self, count:int, ncols:int) -> Tuple[int, int, int, int]:
        """ Return bounding box coordinates for a grid with <count> cells in <ncols> columns. """
        nrows = ceil(count / ncols)
        return (self._left, self._top, self._width * ncols, self._height * nrows)
