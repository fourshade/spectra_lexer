""" Module for generating steno board diagram elements and transforms. """

from math import ceil
from typing import List, Sequence, Tuple

from .svg import SVGDocument, SVGElement, SVGGroup

STROKE_SENTINEL = SVGElement()


class BoardGenerator:
    """ Generates the final board data with transforms fitted to the bounds of the display widget. """

    _bases: List[SVGElement]  # Base elements of the diagram, positioned first in every stroke.
    _bounds: Sequence[int]    # (x, y, w, h) sequence of coordinates for the viewbox on one stroke diagram.

    def __init__(self, bases:List[SVGElement], bounds:Sequence[int]):
        self._bases = bases
        self._bounds = bounds

    def __call__(self, elems:List[SVGElement], ratio:float) -> bytes:
        """ Compute offsets for each stroke on the board diagram. Complete strokes are tiled in a grid layout. """
        last = []
        groups = []
        for elem in [*elems, STROKE_SENTINEL]:
            if elem is STROKE_SENTINEL:
                groups.append(SVGGroup([*self._bases, *last]))
                last = []
            else:
                last.append(elem)
        x, y, w, h = self._bounds
        rows, cols = _arrange(len(groups), w / h, ratio)
        # Add each stroke to a new group, transform it, and encode the entire document when finished.
        for i, group, in enumerate(groups):
            # Subdiagrams are tiled left-to-right, top-to-bottom.
            step_y, step_x = divmod(i, cols)
            group.transform(1, 1, w * step_x, h * step_y)
        document = SVGDocument(groups, viewBox=f"{x} {y} {w * cols} {h * rows}")
        return document.encode()


def _arrange(count:int, board_ratio:float, full_ratio:float) -> Tuple[int, int]:
    """ Calculate the best arrangement of <count> sub-diagrams in rows and columns for the best possible scale.
        <board_ratio> is the aspect ratio of one diagram; <full_ratio> is that of the full viewing area. """
    short_ratio, long_ratio = sorted([board_ratio, full_ratio])
    rel_ratio = count * short_ratio / long_ratio
    if rel_ratio < 1:
        # If the longer aspect ratio is greater than the count, place all sub-diagrams across that dimension.
        s, l = 1, count
    else:
        # Find the two possibilities for optimum arrangement and choose the one with the larger scale.
        s_exact = rel_ratio ** 0.5
        sl_bounds = [(s, ceil(count / s)) for s in (int(s_exact), ceil(s_exact))]
        s, l = max(sl_bounds, key=lambda x: min(short_ratio / x[0], long_ratio / x[1]))
    return (s, l) if (board_ratio < full_ratio) else (l, s)
