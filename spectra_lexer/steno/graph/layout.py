from typing import Sequence

from .node import GraphNode, SeparatorNode
from .primitive import Composite


class BaseGraphLayout(Composite):
    """ Abstract class for a graph composite containing one level of child nodes laid out in rows.
        May contain other layouts recursively. """

    parent_width: int  # Total width of the parent, past which endpieces must be added.

    def __init__(self, node:GraphNode) -> None:
        """ Arrange all children according to the layout and connect them. """
        super().__init__()
        self.parent_width = node.bottom_length
        node.body(self.add)
        if node.children:
            # Child objects are added to the layout from left-to-right.
            # Reverse the list at the end in order to ensure that the leftmost objects get drawn last.
            self._layout(node.children)
            self.reverse()

    def _layout(self, nodes:Sequence[GraphNode]) -> None:
        """ Add a row index with every child, in order. Some children may not be included. """
        raise NotImplementedError

    def _first_row(self, node:GraphNode) -> int:
        """ Start nodes three rows down by default.
            Only start two rows down if the node attaches at the bottom with a single connector. """
        return 3 - (node.bottom_length == 1)

    def _connect(self, node:GraphNode, obj:Composite, row:int, col:int) -> None:
        """ Add the connectors and child layout object. """
        overhang = col - self.parent_width + 1
        if overhang > 0:
            node.overhang(self.add, col, overhang)
        node.connectors(self.add, row, col)
        self.add(obj, row, col)


class CascadedGraphLayout(BaseGraphLayout):
    """ Graph layout with nodes in descending order like a waterfall from the top-down going left-to-right.
        Recursive construction with one line per node means everything fits naturally with no overlap.
        Window space economy is poor (the triangle shape means half the space is wasted off the top).
        Aspect ratio is highly vertical, requiring an awkwardly shaped display window to accommodate. """

    def _layout(self, nodes:Sequence[GraphNode]) -> None:
        """ Every time a new node is placed, we simply move down by a number of rows equal to its height. """
        bottom_bound = 0
        right_bound = 0
        for node in nodes:
            # Nodes that have children themselves are recursively laid out first to determine their height and width.
            obj = self.__class__(node)
            col = node.attach_start
            # Advance to the next free row. Move down one more if this child shares columns with the last one.
            row = bottom_bound or self._first_row(node)
            if right_bound > col and type(node) is not SeparatorNode:
                row += 1
            self._connect(node, obj, row, col)
            # Advance the bounds by its height and width.
            bottom_bound = row + obj.height
            right_bound = col + obj.width


class CompressedGraphLayout(BaseGraphLayout):
    """ Graph layout that attempts to arrange nodes and connections in the minimum number of rows.
        Since nodes belonging to different strokes may occupy the same row, no stroke separators are drawn. """

    _MAX_HEIGHT: int = 50  # Graphs should never be taller than this many rows.
    _MAX_WIDTH: int = 50   # Graphs should never be wider than this many columns.

    def _layout(self, nodes:Sequence[GraphNode]) -> None:
        """ Place nodes into rows using a slot-based system. Each node records which row slot it occupies starting from
            the top down, and the rightmost column it needs. After that column, the slot becomes free again. """
        top_bound = 0
        right_bound = 0
        bounds = [-1] * self._MAX_HEIGHT
        for node in nodes:
            obj = self.__class__(node)
            col = node.attach_start
            # Make sure strokes don't run together. Separators will not enter the row list.
            if type(node) is SeparatorNode:
                right_bound = self._MAX_WIDTH
                continue
            start = self._first_row(node)
            # If this node starts where the last one ended and there's no overlap, use the same row.
            row = top_bound
            if col < right_bound or row < start:
                # Search for the next free row from the top down and place the node there.
                height = obj.height
                for r in range(start, self._MAX_HEIGHT):
                    if bounds[r] <= col:
                        if height == 1 or all([b <= col for b in bounds[r+1:r+height]]):
                            row = r
                            break
            self._connect(node, obj, row, col)
            top_bound = row
            bottom_bound = row + obj.height
            right_bound = col + obj.width
            bounds[top_bound:bottom_bound] = [right_bound] * (bottom_bound - top_bound)
            # Prevent other text from starting adjacent to this text (unless handled specially as above).
            bounds[bottom_bound-1] = right_bound + 1
            # Make sure other nodes can't be placed directly above or below this one.
            # Only overwrite safety margins of other nodes if ours is larger.
            for edge in (top_bound - 1, bottom_bound):
                if bounds[edge] < right_bound:
                    bounds[edge] = right_bound
