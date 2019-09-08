""" Module for arranging and rendering text graph objects into a character grid format. """

from typing import Iterable, Iterator, List, Optional, Tuple

from .render import Canvas, GraphNode


class BaseGraphLayout:
    """ Abstract class for a text graph node layout engine. """

    def __init__(self, max_width=50, max_height=50) -> None:
        self._max_width = max_width    # Graphs should never be wider than this many columns.
        self._max_height = max_height  # Graphs should never be taller than this many rows.

    def render(self, root:GraphNode) -> Canvas:
        """ Lay out and render a root graph node on a new canvas. """
        items = [(root, 0, 0, self._layout(root))]
        _, h, w, _ = root.layout_params()
        canvas = Canvas(h, w)
        self._render_recursive(canvas, 0, 0, items)
        return canvas

    def _layout(self, node:GraphNode) -> List[tuple]:
        """ Arrange each child node in rows and return a nested list containing the nodes and their positions. """
        items = []
        children = [*node]
        if children:
            # Children are recursively laid out first to determine their height and width.
            bodies = [*map(self._layout, children)]
            params = [child.layout_params() for child in children]
            rows = self._iter_rows(params)
            widths = []
            heights = []
            # Reverse the composition order to ensure that the leftmost objects get drawn last.
            for child, child_items, row, (col, h, w, _) in reversed([*zip(children, bodies, rows, params)]):
                if row is not None:
                    items.append((child, row, col, child_items))
                    widths.append(col + w)
                    heights.append(row + h)
            node.resize(widths, heights)
        return items

    def _render_recursive(self, canvas:Canvas, parent_row:int, parent_col:int, items:List[tuple]) -> None:
        """ Render each item on the canvas with respect to its parent. """
        for node, row, col, c_items in items:
            this_row = parent_row + row
            this_col = parent_col + col
            if c_items:
                self._render_recursive(canvas, this_row, this_col, c_items)
            node.write(canvas, parent_row, this_row, this_col)

    def _iter_rows(self, node_params:Iterable[Tuple[int, int, int, bool]]) -> Iterator[Optional[int]]:
        """ Lay out nodes using tuples of <node_params> and yield the row index for each.
            All row indices are relative to the parent node at index 0 and going down.
            If a node should not be displayed, yield None for its row index. """
        raise NotImplementedError


class CascadedGraphLayout(BaseGraphLayout):
    """ Graph layout engine that places nodes in descending order like a waterfall from the top down.
        Recursive construction with one line per node means everything fits naturally with no overlap.
        Window space economy is poor (the triangle shape means half the space is wasted off the top).
        Aspect ratio is highly vertical, requiring an awkwardly shaped display window to accommodate. """

    def _iter_rows(self, node_params:Iterable[Tuple[int, int, int, bool]]) -> Iterator[Optional[int]]:
        """ Every time a new node is placed, we simply move down by a number of rows equal to its height. """
        row = 0
        right_bound = 0
        for start_col, height, width, min_row in node_params:
            # Move to the next free row, plus one more if this child shares columns with the last one.
            if row < min_row:
                row = min_row
            if right_bound > start_col and width:
                row += 1
            # Place the child at the current position and advance the bounds.
            yield row
            row += height
            right_bound = start_col + width


class CompressedGraphLayout(BaseGraphLayout):
    """ Graph layout engine that attempts to arrange nodes and connections in the minimum number of rows.
        Since nodes belonging to different strokes may occupy the same row, no stroke separators are drawn. """

    def _iter_rows(self, node_params:Iterable[Tuple[int, int, int, bool]]) -> Iterator[Optional[int]]:
        """ Place nodes into rows using a slot-based system. Each node records which row slot it occupies starting from
            the top down, and the rightmost column it needs. After that column passes, the slot becomes free again. """
        row = 0
        right_bound = 0
        slots = [-1] * self._max_height
        for start_col, height, width, min_row in node_params:
            # Separators will not enter the row list.
            if not min_row:
                right_bound = self._max_width
                yield None
                continue
            # If this node starts where the last one ended and there's no overlap, use the same row.
            if start_col < right_bound or row < min_row:
                # Search for the next free row from the top down and place the node there.
                for r in range(min_row, self._max_height):
                    if slots[r] <= start_col:
                        if height == 1 or all([b <= start_col for b in slots[r+1:r+height]]):
                            row = r
                            break
                else:
                    # What monstrosity is this? Put the next row wherever.
                    row = min_row
            # Place the child at the current position and advance the bounds.
            yield row
            top_bound = row
            bottom_bound = row + height
            right_bound = start_col + width
            slots[top_bound:bottom_bound] = [right_bound] * (bottom_bound - top_bound)
            # Prevent other text from starting adjacent to this text (unless handled specially as above).
            slots[bottom_bound-1] = right_bound + 1
            # Make sure other nodes can't be placed directly above or below this one.
            # Only overwrite safety margins of other nodes if ours is larger.
            for edge in (top_bound - 1, bottom_bound):
                if slots[edge] < right_bound:
                    slots[edge] = right_bound
