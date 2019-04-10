""" Module for generating steno board diagram element bounds. """

from math import ceil
from typing import List, Tuple


class ElementLayout:
    """ Generates a list of board graphical elements fitted to the bounds of the display widget. """

    _view: tuple = (0, 0, 10, 10)  # (x, y, w, h) tuple of coordinates for the unscaled viewbox.
    _width: int = 0                # Total width of the diagram widget in pixels.
    _height: int = 0               # Total height of the diagram widget in pixels.

    def set_view(self, view:tuple) -> None:
        """ Set the current size of the SVG viewbox. """
        self._view = view

    def set_size(self, width:int, height:int) -> None:
        """ Set the current size of the widget in pixels. """
        self._width = width
        self._height = height

    def make_draw_list(self, ids:List[List[str]]) -> List[tuple]:
        """ Compute the offset and scale for each element ID in each stroke on the board diagram.
            Complete strokes are tiled in a grid layout, scaled to the maximum area of the widget. """
        rows, cols, scale = self._arrange(len(ids))
        # Find the global offsets needed to center everything in the widget at maximum scale.
        sx, sy, sw, sh = [c * scale for c in self._view]
        ox = -sx + (self._width - (sw * cols)) / 2
        oy = -sy + (self._height - (sh * rows)) / 2
        # Subdiagrams are tiled left-to-right, top-to-bottom. Find the top-left corner of each one and add the strokes.
        return [(stroke, scale, ox + sw * (i % cols), oy + sh * (i // cols)) for i, stroke in enumerate(ids)]

    def _arrange(self, count:int) -> Tuple[int, int, float]:
        """ Calculate the best arrangement of sub-diagrams in rows and columns and the maximum possible scale. """
        w_ratio = self._width / self._view[2]
        h_ratio = self._height / self._view[3]
        short_ratio, long_ratio = sorted([w_ratio, h_ratio])
        rel_ratio = long_ratio / short_ratio
        if rel_ratio >= count:
            # If the longer aspect ratio is greater than the count, place all subdiagrams across that dimension.
            s, l, scale = 1, count, short_ratio
        else:
            # Find the two possibilities for optimum arrangement and choose the one with the larger scale.
            s_exact = (count / rel_ratio) ** 0.5
            sl_bounds = [(s, ceil(count / s)) for s in (int(s_exact), ceil(s_exact))]
            out = [(s, l, min(short_ratio / s, long_ratio / l)) for s, l in sl_bounds]
            s, l, scale = max(out, key=lambda x: x[2])
        return (s, l, scale) if (w_ratio > h_ratio) else (l, s, scale)
