from collections import defaultdict
from typing import Dict, Iterable, Iterator, List, Sequence, Set, TypeVar, Tuple

from .base import GraphLayout, IBody, IConnectors, LayoutNode, TextElement, TextElementGrid


class GridCanvas:
    """ A mutable 2D grid for drawing generic elements in a random-access manner. """

    _ELEMENT = TypeVar("_ELEMENT")

    def __init__(self, nrows:int, ncols:int, empty:_ELEMENT) -> None:
        """ Make a new, blank grid by copying a single list repeatedly. """
        assert nrows >= 0 and ncols >= 0
        self._grid = [*map(list.copy, [[empty] * ncols] * nrows)]  # String data grid; a list of lists.
        self._empty = empty   # Empty grid element. Used for initialization and padding.
        self._row_offset = 0  # Offset in rows to add to every write command.
        self._col_offset = 0  # Offset in columns to add to every write command.

    def write(self, el:_ELEMENT, row:int, col:int) -> None:
        """ Write an element at <row, col>. """
        row += self._row_offset
        if row < 0:
            self._shift_rows(-row)
            row = 0
        col += self._col_offset
        if col < 0:
            self._shift_cols(-col)
            col = 0
        self._grid[row][col] = el

    def write_row(self, seq:Iterable[_ELEMENT], row:int, col:int) -> None:
        """ Write an element <seq>uence across a row with the top-left starting at <row, col>. """
        row += self._row_offset
        if row < 0:
            self._shift_rows(-row)
            row = 0
        col += self._col_offset
        if col < 0:
            self._shift_cols(-col)
            col = 0
        r = self._grid[row]
        for s in seq:
            r[col] = s
            col += 1

    def replace_empty(self, repl:_ELEMENT, row:int) -> None:
        """ Replace all empty elements in a entire row with <repl>. """
        row += self._row_offset
        r = self._grid[row]
        for col, item in enumerate(r):
            if item is self._empty:
                r[col] = repl

    def _shift_rows(self, nrows:int) -> None:
        """ Pad the grid with empty rows at the top to compensate for an object drawing at a negative index. """
        self._row_offset += nrows
        ncols = len(self._grid[0])
        empty_row = [self._empty] * ncols
        self._grid[:0] = map(list.copy, [empty_row] * nrows)

    def _shift_cols(self, ncols:int) -> None:
        """ Pad the grid with empty columns to the left to compensate for an object drawing at a negative index. """
        self._col_offset += ncols
        padding = [self._empty] * ncols
        for r in self._grid:
            r[:0] = padding

    def to_lists(self) -> List[List[_ELEMENT]]:
        """ Return the contents of the grid as a list of lists. """
        return list(map(list.copy, self._grid))

    def __str__(self) -> str:
        """ Return all grid elements joined into a single string with default line ends. """
        sections = []
        for r in self._grid:
            sections += map(str, r)
            sections.append("\n")
        return "".join(sections)


class GraphNode(LayoutNode):
    """ A standard node in a tree structure of steno rules. """

    def __init__(self, ref:str, body:IBody, connectors:IConnectors,
                 tstart:int, tlen:int, children:Sequence["GraphNode"]) -> None:
        self._ref = ref                # Reference string that is guaranteed to be unique in the tree.
        self._body = body              # The node's "body" containing steno keys or English text.
        self._connectors = connectors  # Pattern constructor for connectors.
        self._attach_start = tstart    # Index of the starting character in the parent node where this node attaches.
        self._attach_length = tlen     # Length in characters of the attachment to the parent node.
        self._children = children      # Direct children of this node.

    def children(self) -> Sequence["GraphNode"]:
        """ Return all direct children of this node. """
        return self._children

    def min_row(self) -> int:
        """ Minimum row spacing is determined by the connectors. """
        return self._connectors.min_height()

    def start_col(self) -> int:
        """ attach_start is the left column index for the node body relative to the parent. """
        return self._attach_start

    def min_height(self) -> int:
        """ Return the height of the node body as the smallest possible height. """
        return self._body.height()

    def min_width(self) -> int:
        """ Return the width of the node body as the smallest possible width. """
        return self._body.width()

    def is_separator(self) -> bool:
        return self._body.is_separator()

    def iter_elements(self, top_row:int, bottom_row:int, col:int,
                      successors:Dict[int, Set[str]]) -> Iterator[Tuple[int, int, str, str, int, set]]:
        body = self._body
        body_col, text = body.text(col)
        ref = self._ref
        for i in range(self._attach_length):
            successors[i+col].add(ref)
        bold_at = 1 - body.is_always_bold()
        for char in text:
            triggers = {ref, *successors[body_col]}
            yield bottom_row, body_col, char, ref, bold_at, triggers
            body_col += 1
        height = bottom_row - top_row
        if height:
            triggers = {ref}.union(*successors.values())
            row = top_row
            for s in self._connectors.strlist(height):
                c = col
                for char in s:
                    yield row, c, char, ref, 100, triggers
                    c += 1
                row += 1


class TextElementCanvas:

    _EMPTY = TextElement(" ")

    def __init__(self, canvas:GridCanvas) -> None:
        self._canvas = canvas

    def to_grid(self) -> TextElementGrid:
        """ Return the contents of the canvas as a list grid. """
        return self._canvas.to_lists()

    def write_layout(self, layout:GraphLayout, parent_top=0, parent_left=0, depth=0) -> Dict[int, Set[str]]:
        """ Draw text elements on the canvas recursively from a layout. """
        node = layout.node
        top = parent_top + layout.top
        left = parent_left + layout.left
        successors = defaultdict(set)
        for sublayout in layout.sublayouts:
            triggers = self.write_layout(sublayout, top, left, depth + 1)
            for i, s in triggers.items():
                successors[i].update(s)
        it = node.iter_elements(parent_top, top, left, successors)
        if node.is_separator():
            # Replace every element in the bottom row with the separator.
            row, col, char, *_ = next(it)
            elem = TextElement(char)
            self._canvas.replace_empty(elem, row)
        else:
            for row, col, char, ref, bold_at, triggers in it:
                elem = TextElement(char, ref, depth, bold_at, triggers)
                self._canvas.write(elem, row, col)
        return successors

    @classmethod
    def from_layout(cls, layout:GraphLayout) -> "TextElementCanvas":
        """ Make a new canvas from the dimensions of the layout and draw it. """
        canvas = GridCanvas(layout.bottom, layout.right, cls._EMPTY)
        self = cls(canvas)
        self.write_layout(layout)
        return self
