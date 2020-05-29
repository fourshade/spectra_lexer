from math import ceil, cos, pi, sin
from typing import Sequence, Tuple


class TransformData:
    """ Data for a 2D affine transformation. """

    def __init__(self) -> None:
        self._scale_x = 1.0
        self._shear_y = 0.0
        self._shear_x = 0.0
        self._scale_y = 1.0
        self._dx = 0.0
        self._dy = 0.0
        self._simple = True

    @classmethod
    def translation(cls, dx:float, dy:float) -> "TransformData":
        """ Shortcut for creating a blank transform and translating it. """
        self = cls()
        self.translate(dx, dy)
        return self

    def offset(self) -> complex:
        """ Return the current translation offset in complex form. """
        return self._dx + self._dy * 1j

    def rotate(self, degrees:float) -> None:
        """ Rotate the system <degrees> counterclockwise. """
        theta = degrees * pi / 180
        self._scale_x = cos(theta)
        self._shear_y = -sin(theta)
        self._shear_x = sin(theta)
        self._scale_y = cos(theta)
        self._simple = False

    def scale(self, scale_x:float, scale_y:float) -> None:
        """ Scale the system by a decimal amount. """
        self._scale_x *= scale_x
        self._scale_y *= scale_y
        self._simple = False

    def translate(self, dx:float, dy:float) -> None:
        """ Translate (move) the system by an additional offset of <dx, dy>. """
        self._dx += dx
        self._dy += dy

    def to_string(self) -> str:
        """ A linear transform with scaling, rotation, translation, etc. can be done in one step with a matrix. """
        dx = self._dx
        dy = self._dy
        if self._simple:
            # If only one type of transformation is involved, use the simpler attributes.
            if not dx and not dy:
                return ''
            return f'translate({dx}, {dy})'
        return f'matrix({self._scale_x}, {self._shear_y}, {self._shear_x}, {self._scale_y}, {dx}, {dy})'


class GridLayoutEngine:
    """ Calculates dimensions and transforms for items arranged in a grid. """

    def __init__(self, left:int, top:int, width:int, height:int) -> None:
        self._left = left      # X offset for the full grid.
        self._top = top        # Y offset for the full grid.
        self._width = width    # Width of a single cell.
        self._height = height  # Height of a single cell.

    def arrange(self, count:int, aspect_ratio:float) -> Tuple[int, int]:
        """ Calculate the best arrangement of <count> cells in rows and columns
            for the best possible scale in a viewing area of <aspect_ratio>. """
        diagram_ratio = self._width / self._height
        # rel_ratio is the aspect ratio of one cell divided by that of the viewing area.
        rel_ratio = diagram_ratio / aspect_ratio
        r = min(rel_ratio, 1 / rel_ratio)
        s = int((count * r) ** 0.5) or 1
        if r * ceil(count / s) > (s + 1):
            s += 1
        t = ceil(count / s)
        return (s, t) if rel_ratio < 1 else (t, s)

    def _offset_tfrm(self, i:int, ncols:int) -> TransformData:
        """ Create a (dx, dy) translation for row-major cell <i> in a grid with <ncols> columns. """
        dx = self._width * (i % ncols)
        dy = self._height * (i // ncols)
        return TransformData.translation(dx, dy)

    def transforms(self, count:int, ncols:int) -> Sequence[TransformData]:
        """ Create evenly spaced offset transformations for a grid with <count> cells in <ncols> columns. """
        return [self._offset_tfrm(i, ncols) for i in range(count)]

    def viewbox(self, rows:int, cols:int) -> Tuple[int, int, int, int]:
        """ Return the final offset and dimensions for a grid of size <rows, cols>. """
        return (self._left, self._top, self._width * cols, self._height * rows)
