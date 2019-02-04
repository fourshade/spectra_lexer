""" Module for generating steno board diagram element bounds. """

from math import ceil
from typing import Dict, List, Tuple


class ElementLayout:
    """ Generates a list of board graphical elements fitted to the bounds of the display widget. """

    _bounds_dict: Dict[str, tuple]  # (x, y, w, h) bounds of each graphical element by id.
    _view_box: tuple                # (x, y, w, h) bounds of the SVG view box for the root element.

    def __init__(self, d:Dict[str, tuple], view_box:tuple):
        self._bounds_dict = d
        self._view_box = view_box

    def generate(self, ids:List[List[str]], width:int, height:int) -> List[tuple]:
        """ Compute the new drawing bounds for each element on the board diagram.
            Each diagram is tiled in a grid layout, scaled to the maximum area of the widget. """
        draw_list = []
        d = self._bounds_dict
        w_ratio = width / self._view_box[2]
        h_ratio = height / self._view_box[3]
        rows, cols, scale = _arrange(w_ratio, h_ratio, len(ids))
        # Find the global offsets needed to center everything in the widget at maximum scale.
        sx, sy, sw, sh = [c * scale for c in self._view_box]
        ox = -sx + (width - (sw * cols)) / 2
        oy = -sy + (height - (sh * rows)) / 2
        # Subdiagrams are tiled left-to-right, top-to-bottom. Find the top-left corner of each one.
        for i, stroke in enumerate(ids):
            steps_y, steps_x = divmod(i, cols)
            offset_x = ox + sw * steps_x
            offset_y = oy + sh * steps_y
            # Place each element within its scaled, offset-adjusted bounds.
            for k in stroke:
                x, y, w, h = [c * scale for c in d[k]]
                draw_list.append((k, x + offset_x, y + offset_y, w, h))
        return draw_list


def _arrange(w_ratio:float, h_ratio:float, count:int) -> Tuple[int, int, float]:
    """ Calculate the best arrangement of sub-diagrams in rows and columns and the maximum possible scale. """
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
