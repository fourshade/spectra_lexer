from collections import defaultdict
from typing import Dict, List, Set

from .body import IBody
from .canvas import GridCanvas
from .connectors import IConnectors
from .format import TextElement, TextElementGrid
from .layout import GraphLayout, LayoutParams

SuccessorsDict = Dict[int, Set[str]]   # Dictionary of a node's successor references by depth.
TextCanvas = GridCanvas[TextElement]   # Text graph element canvas.

EMPTY_ELEMENT = TextElement(" ")       # Blank text graph element with no markup or references.


class GraphNode:
    """ Represents a node in a tree structure of steno rules. Each node may have zero or more children. """

    _top = 0   # Current row for top of node body.
    _left = 0  # Current column for left side of node body.

    def __init__(self, ref:str, body:IBody, connectors:IConnectors,
                 tstart:int, tlen:int, children:List["GraphNode"]) -> None:
        self._ref = ref                # Reference string that is guaranteed to be unique in the tree.
        self._body = body              # The node's "body" containing steno keys or English text.
        self._connectors = connectors  # Pattern constructor for connectors.
        self._attach_start = tstart    # Index of the starting character in the parent node where this node attaches.
        self._attach_length = tlen     # Length in characters of the attachment to the parent node.
        self._children = children      # List of direct children of this node.

    def move(self, row:int, col:int) -> None:
        """ Move the top-left corner of this node's body to <row, col>. """
        self._top = row
        self._left = col

    def layout(self, layout:GraphLayout) -> LayoutParams:
        """ Arrange each child node in rows and return the combined bounds. """
        # Minimum vertical spacing from the parent is determined by the connectors.
        top = self._connectors.min_height()
        # attach_start is the column index for the left side of the node body relative to the parent.
        left = self._attach_start
        # Our own node body is the smallest possible width and height.
        h = self._body.height()
        w = self._body.width()
        children = self._children
        if children:
            # Children are recursively laid out first to determine their height and width.
            params = [child.layout(layout) for child in children]
            # Arrange (or remove) children and calculate total width and height from the maximum child bounds.
            for child, output in zip(children[:], layout.arrange(params)):
                if output is None:
                    children.remove(child)
                else:
                    tb, lb, bb, rb = output
                    child.move(tb, lb)
                    if bb > h:
                        h = bb
                    if rb > w:
                        w = rb
        return top, left, h, w

    def _draw_normal(self, canvas:TextCanvas, top_row:int, bottom_row:int, col:int,
                     depth:int, successors:SuccessorsDict) -> None:
        """ Draw the text body and connectors (if any) on the canvas. """
        ref = self._ref
        for i in range(self._attach_length):
            successors[i+col].add(ref)
        body = self._body
        body_col = col + body.offset()
        text = body.text()
        bold_at = 1 - body.is_always_bold()
        for char in text:
            triggers = {ref, *successors[body_col]}
            elem = TextElement(char, ref, depth, bold_at, triggers)
            canvas.write(elem, bottom_row, body_col)
            body_col += 1
        height = bottom_row - top_row
        if height:
            triggers = {ref}.union(*successors.values())
            row = top_row
            for s in self._connectors.rows(height):
                c = col
                for char in s:
                    elem = TextElement(char, ref, depth, 100, triggers)
                    canvas.write(elem, row, c)
                    c += 1
                row += 1

    def _draw_sep(self, canvas:TextCanvas, row:int) -> None:
        """ Replace every element in the <row> with the separator. """
        text = self._body.text()
        elem = TextElement(text)
        canvas.replace_empty(elem, row)

    def draw(self, canvas:TextCanvas, parent_top:int, parent_left:int, depth:int) -> SuccessorsDict:
        """ Draw text elements on a canvas recursively from this node. """
        top = parent_top + self._top
        left = parent_left + self._left
        successors = defaultdict(set)
        # Reverse the composition order to ensure that the leftmost children get drawn last.
        for child in self._children[::-1]:
            triggers = child.draw(canvas, top, left, depth + 1)
            for i, s in triggers.items():
                successors[i].update(s)
        if self._body.is_separator():
            self._draw_sep(canvas, top)
        else:
            self._draw_normal(canvas, parent_top, top, left, depth, successors)
        return successors

    def render(self, layout:GraphLayout) -> TextElementGrid:
        self.layout(layout)
        canvas = TextCanvas(EMPTY_ELEMENT)
        self.draw(canvas, 0, 0, 0)
        return canvas.to_lists()
