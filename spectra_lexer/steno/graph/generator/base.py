""" Module controlling the layout of text graphs, including construction and placement of all drawable objects. """

from itertools import chain
from operator import attrgetter
from typing import List, NamedTuple

from .object import ObjectNode, ObjectNodeUnmatched
from .pattern import PatternInversion, PatternNode, PatternSeparators, PatternThick, PatternUnmatched
from ..node import GraphNode, GraphNodeAppearance
from spectra_lexer.types import delegate_to


class ConnectionInfo(NamedTuple):
    """ Contains a child object with all information about where it should attach relative to its parent. """
    child: ObjectNode  # Child text object.
    height: int        # Text height (including children) in rows.
    width: int         # Text width (including children) in columns.
    appearance: str    # Appearance text flag.
    col: int           # Main attach column.
    t_span: int        # Top attachment length.
    b_shift: int       # Bottom left-shift.
    b_span: int        # Bottom attachment length.


# Convenience function to get all relevant layout coordinates from attributes of a child node.
_NODE_COORDS = attrgetter("appearance", "attach_start", "attach_length", "bottom_start", "bottom_length")


class TextGenerator:
    """ Creates drawable text objects from a node. Layouts arrange the children however they want.
        render() produces the text lines and child node references making it up. """

    # Appearance flag table with custom object and pattern constructor types.
    NODE_DEFAULT = (ObjectNode, PatternNode)
    NODE_APPEARANCE = {GraphNodeAppearance.SEPARATOR: (ObjectNode, PatternSeparators),
                       GraphNodeAppearance.UNMATCHED: (ObjectNodeUnmatched, PatternUnmatched),
                       GraphNodeAppearance.INVERSION: (ObjectNode, PatternInversion),
                       GraphNodeAppearance.BRANCH:    (ObjectNode, PatternThick)}

    _root_object: ObjectNode  # Main container for drawable text objects.

    def __init__(self, root:GraphNode):
        """ Make a tree of text objects to display for a node. The layout depends on the config settings. """
        self._root_object = self.generate(root)

    def generate(self, node:GraphNode) -> ObjectNode:
        """ Look up the type and pattern for this node based on the appearance flag and create the object. """
        obj_tp, pattern = self.NODE_APPEARANCE.get(node.appearance, self.NODE_DEFAULT)
        obj = obj_tp(node.text, node, pattern)
        # If there are children, generate them all recursively, lay them out in rows, and connect them.
        if node.children:
            child_objs = map(self.generate, node.children)
            child_attrs = map(_NODE_COORDS, node.children)
            child_info = [ConnectionInfo(c, c.height, c.width, *a) for c, a in zip(child_objs, child_attrs)]
            rows = self.layout(child_info)
            self.connect(obj, child_info, rows)
        return obj

    def layout(self, info:List[ConnectionInfo]) -> List[int]:
        """ Subclasses must choose a row for each child. """
        raise NotImplementedError

    def connect(self, parent:ObjectNode, info:List[ConnectionInfo], rows:List[int]) -> None:
        """ Connect each child to <parent> at the corresponding row in the layout. """
        for (child, _, _, _, col, t_span, b_shift, b_span), row in zip(info, rows):
            # Draw the connectors on the parent with the bottom-left corner at (row, col).
            child.draw_connectors(parent, col, t_span, row, col, b_span)
            # Actually attach the child at (row, col - shift) to account for hyphens.
            child.attach(parent, row, col - b_shift)
        # Reverse the list of children in order to ensure that the leftmost objects get drawn last.
        parent.reverse()

    render = delegate_to("_root_object")


class CascadedTextGenerator(TextGenerator):
    """
    Nodes are drawn in descending order like a waterfall going left-to-right.
    Recursive construction with one line per node means everything fits naturally with no overlap.
    Window space economy is poor (the triangle shape means half the space is wasted off the top).
    Aspect ratio is highly vertical, requiring an awkwardly shaped display window to accommodate.
    """

    def layout(self, info:List[ConnectionInfo]) -> List[int]:
        """ Allocate rows from the top-down with spacing according to each child's finished size. """
        rows = []
        # Start the first child three rows down, or only two if it attaches at the bottom with a single connector.
        row = 3 - (info[0].b_span == 1)
        right_bound = 0
        for _, height, width, appearance, col, _, b_shift, b_span in info:
            # Advance to the next free row. Move down one more if this child shares columns with the last one.
            row += (right_bound > col and appearance != GraphNodeAppearance.SEPARATOR)
            rows.append(row)
            # Advance the bounds by this child's height and width.
            row += height
            right_bound = col + width - b_shift
        return rows


class CompressedTextGenerator(TextGenerator):
    """ Text generator that attempts to arrange nodes and connections in the minimum number of rows.
        Since nodes belonging to different strokes may occupy the same row, no stroke separators are drawn. """

    def layout(self, info:List[ConnectionInfo], _start=3, _end=50) -> List[int]:
        """ Allocate rows from the top-down as efficiently as possible to keep a rectangular shape. """
        rows = []
        row = _start
        right_bound = _end
        bounds = [-1] * _end
        # Place nodes into rows using a slot-based system. Each node records which row slot it occupies starting from
        # the top down, and the rightmost column it needs. After that column is passed, the slot becomes free again.
        for _, height, width, appearance, col, _, b_shift, b_span in info:
            # Make sure strokes don't run together.
            if appearance == GraphNodeAppearance.SEPARATOR:
                right_bound = _end
                continue
            # Index 2 can only be occupied by nodes that attach at the bottom with a single connector.
            rng = range(_start - (b_span == 1), _end)
            # If this node starts where the last one ended, attempt the slot next to it first.
            if col >= right_bound and row in rng:
                bounds[row] -= 1
                rng = chain((row,), rng)
            # Search for the next free slot from the top down and place the node there.
            for r in rng:
                if bounds[r] <= col:
                    if height == 1 or all(bounds[i] <= col for i in range(r + 1, r + height)):
                        row = r
                        break
            rows.append(row)
            # Make sure other nodes can't be placed directly above or below this one.
            bottom_bound = row + height
            right_bound = col + width - b_shift
            # Only overwrite the safety margins of other nodes if ours is larger.
            bounds[row - 1] = max(right_bound, bounds[row - 1])
            for i in range(row, bottom_bound):
                bounds[i] = right_bound + 1
            bounds[bottom_bound] = max(right_bound, bounds[bottom_bound])
        # Filter out all stroke separators from the info list.
        info[:] = [i for i in info if i.appearance != GraphNodeAppearance.SEPARATOR]
        return rows
