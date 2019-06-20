from typing import Iterable

from .node import GraphNode, SeparatorNode
from .primitive import Composite


class GraphLayout(Composite):

    _START_ROW: int = 3  # Start the first child three rows down by default.

    def __init__(self, node:GraphNode):
        """ Arrange all children according to the layout and connect them. Some children may not be included. """
        super().__init__()
        node.body(self.add)
        if node.children:
            self._layout(node.children, node.bottom_length)
            # Reverse the list in order to ensure that the leftmost objects get drawn last.
            self.reverse()

    def _layout(self, nodes:Iterable[GraphNode], p_width:int) -> None:
        """ Add a row index with every child, in order. To filter out a child, do not use that iteration. """
        raise NotImplementedError


class CascadedGraphLayout(GraphLayout):

    def _layout(self, nodes:Iterable[GraphNode], p_width:int) -> None:
        """ Nodes are drawn in descending order like a waterfall from the top-down going left-to-right.
            Recursive construction with one line per node means everything fits naturally with no overlap.
            Window space economy is poor (the triangle shape means half the space is wasted off the top).
            Aspect ratio is highly vertical, requiring an awkwardly shaped display window to accommodate. """
        row = None
        right_bound = 0
        for node in nodes:
            # Only start two rows down if the first child attaches at the bottom with a single connector.
            if row is None:
                row = self._START_ROW - (node.bottom_length == 1)
            # Advance to the next free row. Move down one more if this child shares columns with the last one.
            obj = self.__class__(node)
            col = node.attach_start
            row += (right_bound > col and type(node) is not SeparatorNode)
            # Add the connectors and child layout object. Advance the bounds by its height and width.
            node.connectors(self.add, row, col, p_width)
            self.add(obj, row, col)
            row += obj.height
            right_bound = col + obj.width


class CompressedGraphLayout(GraphLayout):

    _MAX_WIDTH: int = 50  # Graphs should never be wider than this many columns.

    def _layout(self, nodes:Iterable[GraphNode], p_width:int) -> None:
        """ Graph layout that attempts to arrange nodes and connections in the minimum number of rows.
            Since nodes belonging to different strokes may occupy the same row, no stroke separators are drawn. """
        row = self._START_ROW
        end = right_bound = self._MAX_WIDTH
        bounds = [-1] * end
        # Place nodes into rows using a slot-based system. Each node records which row slot it occupies starting from
        # the top down, and the rightmost column it needs. After that column is passed, the slot becomes free again.
        for node in nodes:
            obj = self.__class__(node)
            col = node.attach_start
            # Make sure strokes don't run together. Separators will not enter the row list.
            if type(node) is SeparatorNode:
                right_bound = end
                continue
            # Index 2 can only be occupied by nodes that attach at the bottom with a single connector.
            start = self._START_ROW - (node.bottom_length == 1)
            valid_range = range(start, end)
            # If this node starts where the last one ended, attempt the slot next to it first.
            if col >= right_bound and row >= start:
                bounds[row] -= 1
                valid_range = [row, *valid_range]
            # Search for the next free slot from the top down and place the node there.
            height = obj.height
            for r in valid_range:
                if bounds[r] <= col:
                    if height == 1 or all(b <= col for b in bounds[r+1:r+height]):
                        row = r
                        break
            node.connectors(self.add, row, col, p_width)
            self.add(obj, row, col)
            # Make sure other nodes can't be placed directly above or below this one.
            bottom_bound = row + height
            right_bound = col + obj.width
            # Only overwrite the safety margins of other nodes if ours is larger.
            bounds[row - 1] = max(right_bound, bounds[row - 1])
            for i in range(row, bottom_bound):
                bounds[i] = right_bound + 1
            bounds[bottom_bound] = max(right_bound, bounds[bottom_bound])
