""" Module controlling the layout of text graphs, including construction and placement of all drawable objects. """

from itertools import chain
from typing import Callable, Iterable, List, Sequence, Tuple

from .object import ObjectNode, ObjectNodeUnmatched
from .pattern import PatternInversion, PatternNode, PatternSeparators, PatternThick, PatternUnmatched
from ..node import GraphNode

_APPEARANCE_SEPARATOR = GraphNode.Appearance.SEPARATOR
_APPEARANCE_UNMATCHED = GraphNode.Appearance.UNMATCHED
_APPEARANCE_INVERSION = GraphNode.Appearance.INVERSION
_APPEARANCE_BRANCH = GraphNode.Appearance.BRANCH


class TextGenerator:
    """ Creates drawable text objects from a node. Layouts arrange the children however they want.
        render() produces the text lines and child node references making it up. """

    # Appearance flag table with custom object and pattern constructor types.
    _DEFAULT_PATTERN = (ObjectNode, PatternNode)
    _APPEARANCE_TO_PATTERN = {_APPEARANCE_SEPARATOR: (ObjectNode, PatternSeparators),
                              _APPEARANCE_UNMATCHED: (ObjectNodeUnmatched, PatternUnmatched),
                              _APPEARANCE_INVERSION: (ObjectNode, PatternInversion),
                              _APPEARANCE_BRANCH:    (ObjectNode, PatternThick)}

    _layout: Callable         # Function to arrange children in rows.
    _root_object: ObjectNode  # Main container for drawable text objects.

    def __init__(self, root:GraphNode, compressed:bool=False):
        """ Make a tree of text objects to display for a node. The layout depends on the compression setting. """
        self._layout = _layout_compressed if compressed else _layout_cascaded
        self._root_object = self.generate(root)

    def generate(self, node:GraphNode) -> ObjectNode:
        """ Look up the type and pattern for this node based on the appearance flag and create the object. """
        obj_tp, pattern = self._APPEARANCE_TO_PATTERN.get(node.appearance, self._DEFAULT_PATTERN)
        obj = obj_tp(node.text, node, pattern)
        self._add_children(obj, node.children)
        return obj

    def _add_children(self, obj:ObjectNode, child_nodes:Sequence[GraphNode]):
        """ If there are children, generate them all recursively, lay them out in rows, and connect them. """
        if child_nodes:
            child_rows = self._layout(map(self.generate, child_nodes), child_nodes)
            _connect(obj, child_rows)

    def render(self) -> Tuple[list, list]:
        """ Render all text objects onto a grid of the minimum required size. """
        return self._root_object.render()


_START_ROW = 3    # Start the first child three rows down by default.
_MAX_LENGTH = 50  # Graphs should never be wider than this.


def _layout_cascaded(child_objs:Iterable[ObjectNode], child_nodes:Sequence[GraphNode]) -> List[tuple]:
    """ Nodes are drawn in descending order like a waterfall from the top-down going left-to-right.
        Recursive construction with one line per node means everything fits naturally with no overlap.
        Window space economy is poor (the triangle shape means half the space is wasted off the top).
        Aspect ratio is highly vertical, requiring an awkwardly shaped display window to accommodate. """
    child_rows = []
    # Only start two rows down if it attaches at the bottom with a single connector.
    row = _START_ROW - (child_nodes[0].bottom_length == 1)
    right_bound = 0
    for obj, node in zip(child_objs, child_nodes):
        # Advance to the next free row. Move down one more if this child shares columns with the last one.
        col = node.attach_start
        row += (right_bound > col and node.appearance != _APPEARANCE_SEPARATOR)
        child_rows.append((obj, node, row))
        # Advance the bounds by this child's height and width.
        row += obj.height
        right_bound = col + obj.width - node.bottom_start
    return child_rows


def _layout_compressed(child_objs:Iterable[ObjectNode], child_nodes:Sequence[GraphNode]) -> List[tuple]:
    """ Text generator that attempts to arrange nodes and connections in the minimum number of rows.
        Since nodes belonging to different strokes may occupy the same row, no stroke separators are drawn. """
    row = _START_ROW
    end = right_bound = _MAX_LENGTH
    bounds = [-1] * end
    # Place nodes into rows using a slot-based system. Each node records which row slot it occupies starting from
    # the top down, and the rightmost column it needs. After that column is passed, the slot becomes free again.
    child_rows = []
    for obj, node in zip(child_objs, child_nodes):
        col = node.attach_start
        # Make sure strokes don't run together. Separators will not enter the row list.
        if node.appearance == _APPEARANCE_SEPARATOR:
            right_bound = end
            continue
        # Index 2 can only be occupied by nodes that attach at the bottom with a single connector.
        rng = range(_START_ROW - (node.bottom_length == 1), end)
        # If this node starts where the last one ended, attempt the slot next to it first.
        if col >= right_bound and row in rng:
            bounds[row] -= 1
            rng = chain((row,), rng)
        # Search for the next free slot from the top down and place the node there.
        height = obj.height
        for r in rng:
            if bounds[r] <= col:
                if height == 1 or all(bounds[i] <= col for i in range(r + 1, r + height)):
                    row = r
                    break
        child_rows.append((obj, node, row))
        # Make sure other nodes can't be placed directly above or below this one.
        bottom_bound = row + height
        right_bound = col + obj.width - node.bottom_start
        # Only overwrite the safety margins of other nodes if ours is larger.
        bounds[row - 1] = max(right_bound, bounds[row - 1])
        for i in range(row, bottom_bound):
            bounds[i] = right_bound + 1
        bounds[bottom_bound] = max(right_bound, bounds[bottom_bound])
    return child_rows


def _connect(parent:ObjectNode, child_rows:List[Tuple[ObjectNode, GraphNode, int]]) -> None:
    """ Connect each child object to <parent> at the corresponding row in the layout. """
    for obj, node, row in child_rows:
        col = node.attach_start
        # Draw the connectors on the parent with the bottom-left corner at (row, col).
        obj.draw_connectors(parent, col, node.attach_length, row, col, node.bottom_length)
        # Actually attach the child at (row, col - bottom_start) to account for hyphens.
        parent.add(obj, row, col - node.bottom_start)
    # Reverse the list of children in order to ensure that the leftmost objects get drawn last.
    parent.reverse()
