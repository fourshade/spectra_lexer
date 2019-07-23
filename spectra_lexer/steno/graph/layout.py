from typing import Sequence

from .node import GraphNode, SeparatorNode
from .primitive import Composite


class GraphLayout(Composite):

    _START_ROW: int = 3  # Start the first child three rows down by default.

    parent_width: int  # Total width of the parent, past which endpieces must be added.

    def __init__(self, node:GraphNode):
        """ Arrange all children according to the layout and connect them. Some children may not be included. """
        super().__init__()
        self.parent_width = node.bottom_length
        node.body(self.add)
        if node.children:
            self._layout(node.children)
            # Reverse the list in order to ensure that the leftmost objects get drawn last.
            self.reverse()

    def _layout(self, nodes:Sequence[GraphNode]) -> None:
        """ Add a row index with every child, in order. To filter out a child, do not use that iteration. """
        raise NotImplementedError

    def _first_row(self, node:GraphNode):
        return self._START_ROW - (node.bottom_length == 1)

    def _connect(self, node:GraphNode, obj:Composite, row:int, col:int) -> None:
        """ Add the connectors and child layout object. """
        overhang = col - self.parent_width + 1
        if overhang > 0:
            node.overhang(self.add, col, overhang)
        node.connectors(self.add, row, col)
        self.add(obj, row, col)


class CascadedGraphLayout(GraphLayout):
    """ Nodes are drawn in descending order like a waterfall from the top-down going left-to-right.
        Recursive construction with one line per node means everything fits naturally with no overlap.
        Window space economy is poor (the triangle shape means half the space is wasted off the top).
        Aspect ratio is highly vertical, requiring an awkwardly shaped display window to accommodate. """

    def _layout(self, nodes:Sequence[GraphNode]) -> None:
        # Only start two rows down if the first child attaches at the bottom with a single connector.
        row = self._first_row(nodes[0])
        right_bound = 0
        for node in nodes:
            # Advance to the next free row. Move down one more if this child shares columns with the last one.
            obj = self.__class__(node)
            col = node.attach_start
            if right_bound > col and type(node) is not SeparatorNode:
                row += 1
            self._connect(node, obj, row, col)
            # Advance the bounds by its height and width.
            row += obj.height
            right_bound = col + obj.width


class CompressedGraphLayout(GraphLayout):
    """ Graph layout that attempts to arrange nodes and connections in the minimum number of rows.
        Since nodes belonging to different strokes may occupy the same row, no stroke separators are drawn. """

    _MAX_WIDTH: int = 50  # Graphs should never be wider than this many columns.

    def _layout(self, nodes:Sequence[GraphNode]) -> None:
        """ Place nodes into rows using a slot-based system. Each node records which row slot it occupies starting from
            the top down, and the rightmost column it needs. After that column, the slot becomes free again. """
        row = self._START_ROW
        end = right_bound = self._MAX_WIDTH
        bounds = [-1] * end
        for node in nodes:
            obj = self.__class__(node)
            col = node.attach_start
            # Make sure strokes don't run together. Separators will not enter the row list.
            if type(node) is SeparatorNode:
                right_bound = end
                continue
            # Index 2 can only be occupied by nodes that attach at the bottom with a single connector.
            start = self._first_row(node)
            height = obj.height
            # If this node starts where the last one ended and there's no overlap, use the same row.
            if col < right_bound or row < start:
                # Search for the next free row from the top down and place the node there.
                for r in range(start, end):
                    if bounds[r] <= col:
                        if height == 1 or all([b <= col for b in bounds[r+1:r+height]]):
                            row = r
                            break
            self._connect(node, obj, row, col)
            # Make sure other nodes can't be placed directly above or below this one.
            bottom_bound = row + height
            right_bound = col + obj.width
            # Only overwrite the safety margins of other nodes if ours is larger.
            bounds[row - 1] = max(right_bound, bounds[row - 1])
            bounds[row:bottom_bound] = [right_bound + 1] * height
            bounds[bottom_bound] = max(right_bound, bounds[bottom_bound])
