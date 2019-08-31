from typing import Iterable

from .node import GraphNode, SeparatorNode
from .primitive import Composite


class LayoutComposite(Composite):
    """ Composite text graph object created by a graph layout engine. """

    def __init__(self, parent_width:int) -> None:
        super().__init__()
        self._parent_width = parent_width  # Total width of the parent, past which endpieces must be added.

    def connect(self, child:GraphNode, child_obj:Composite, row:int, col:int) -> None:
        """ Add a child graph object to this one with connectors. """
        overhang = col - self._parent_width + 1
        if overhang > 0:
            child.overhang(self.add, col, overhang)
        child.connectors(self.add, row, col)
        self.add(child_obj, row, col)


class BaseGraphLayout:
    """ Abstract class for a layout engine that arranges rows of graph nodes. """

    def __init__(self, top_row=3, max_width=50, max_height=50) -> None:
        self._top_row = top_row        # Starting row for child nodes relative to parent.
        self._max_width = max_width    # Graphs should never be wider than this many columns.
        self._max_height = max_height  # Graphs should never be taller than this many rows.

    def build(self, node:GraphNode) -> LayoutComposite:
        """ Build a new graph object from <node> and arrange all of its children according to the layout. """
        obj = LayoutComposite(node.bottom_length)
        node.body(obj.add)
        if node.children:
            # Reverse the composite list at the end in order to ensure that the leftmost objects get drawn last.
            self._layout(node.children, obj)
            obj.reverse()
        return obj

    def _layout(self, children:Iterable[GraphNode], parent_obj:Composite) -> None:
        """ Lay out <children> in rows and connect them to <parent_obj>. Some children may not be included. """
        raise NotImplementedError

    def _first_row(self, child:GraphNode) -> int:
        """ Start one row higher if the child attaches at the bottom with a single connector. """
        return self._top_row - (child.bottom_length == 1)


class CascadedGraphLayout(BaseGraphLayout):
    """ Graph layout engine that places nodes in descending order like a waterfall from the top down.
        Recursive construction with one line per node means everything fits naturally with no overlap.
        Window space economy is poor (the triangle shape means half the space is wasted off the top).
        Aspect ratio is highly vertical, requiring an awkwardly shaped display window to accommodate. """

    def _layout(self, children:Iterable[GraphNode], parent_obj:LayoutComposite) -> None:
        """ Every time a new node is placed, we simply move down by a number of rows equal to its height. """
        bottom_bound = 0
        right_bound = 0
        for child in children:
            # Nodes that have children themselves are recursively laid out first to determine their height and width.
            child_obj = self.build(child)
            col = child.attach_start
            # Advance to the next free row. Move down one more if this child shares columns with the last one.
            row = bottom_bound or self._first_row(child)
            if right_bound > col and type(child) is not SeparatorNode:
                row += 1
            # Connect the child at the current position.
            parent_obj.connect(child, child_obj, row, col)
            # Advance the bounds by the child's height and width.
            bottom_bound = row + child_obj.height
            right_bound = col + child_obj.width


class CompressedGraphLayout(BaseGraphLayout):
    """ Graph layout engine that attempts to arrange nodes and connections in the minimum number of rows.
        Since nodes belonging to different strokes may occupy the same row, no stroke separators are drawn. """

    def _layout(self, children:Iterable[GraphNode], parent_obj:LayoutComposite) -> None:
        """ Place nodes into rows using a slot-based system. Each node records which row slot it occupies starting from
            the top down, and the rightmost column it needs. After that column, the slot becomes free again. """
        top_bound = 0
        right_bound = 0
        bounds = [-1] * self._max_height
        for child in children:
            child_obj = self.build(child)
            col = child.attach_start
            # Make sure strokes don't run together. Separators will not enter the row list.
            if type(child) is SeparatorNode:
                right_bound = self._max_width
                continue
            start = self._first_row(child)
            # If this node starts where the last one ended and there's no overlap, use the same row.
            row = top_bound
            if col < right_bound or row < start:
                # Search for the next free row from the top down and place the node there.
                height = child_obj.height
                for r in range(start, self._max_height):
                    if bounds[r] <= col:
                        if height == 1 or all([b <= col for b in bounds[r+1:r+height]]):
                            row = r
                            break
            # Connect the child at the current position.
            parent_obj.connect(child, child_obj, row, col)
            # Advance the bounds by the child's height and width.
            bottom_bound = row + child_obj.height
            right_bound = col + child_obj.width
            top_bound = row
            bounds[top_bound:bottom_bound] = [right_bound] * (bottom_bound - top_bound)
            # Prevent other text from starting adjacent to this text (unless handled specially as above).
            bounds[bottom_bound-1] = right_bound + 1
            # Make sure other nodes can't be placed directly above or below this one.
            # Only overwrite safety margins of other nodes if ours is larger.
            for edge in (top_bound - 1, bottom_bound):
                if bounds[edge] < right_bound:
                    bounds[edge] = right_bound
