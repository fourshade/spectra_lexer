""" Module controlling the layout of text graphs, including construction and placement of all drawable objects. """

from operator import attrgetter
from typing import List, NamedTuple, Tuple

from spectra_lexer.graph.text.generator.object import ObjectNode, ObjectNodeUnmatched
from spectra_lexer.graph.text.generator.pattern import *
from spectra_lexer.graph.text.node import TextFlags, TextNode


class ConnectionInfo(NamedTuple):
    """ Contains a child object with all information about where it should attach relative to its parent. """
    child: ObjectNode  # Child text object.
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
    NODE_APPEARANCE = {TextFlags.SEPARATOR: (ObjectNode,          PatternSeparators),
                       TextFlags.UNMATCHED: (ObjectNodeUnmatched, PatternUnmatched),
                       TextFlags.INVERSION: (ObjectNode,          PatternInversion)}

    _root_object: ObjectNode  # Main container for drawable text objects.

    def __init__(self, root:TextNode):
        """ Make a tree of text objects to display for a node. The layout depends on the config settings. """
        self._root_object = self.generate(root)

    def generate(self, node:TextNode) -> ObjectNode:
        """ Look up the type and pattern for this node based on the appearance flag and create the object. """
        obj_tp, pattern = self.NODE_APPEARANCE.get(node.appearance, self.NODE_DEFAULT)
        obj = obj_tp(node.text, node, pattern)
        # If there are children, generate them all recursively, then connect them in a new layout.
        if node.children:
            child_info = [ConnectionInfo(self.generate(c), *_NODE_COORDS(c)) for c in node.children]
            self.connect(obj, child_info)
        return obj

    def connect(self, parent:ObjectNode, info:List[ConnectionInfo]) -> None:
        """ Lay out and connect each child to <parent>. """
        # Find which row to place every child in from the subclass.
        rows = self.layout(info)
        # Connect each child to <parent> at the corresponding row in the layout. """
        for (child, appearance, col, t_span, b_shift, b_span), row in zip(info, rows):
            # Draw the connectors on the parent with the bottom-left corner at (row, col).
            child.draw_connectors(parent, col, t_span, row, col, b_span)
            # Actually attach the child at (row, col - shift) to account for hyphens.
            child.attach(parent, row, col - b_shift)
        # Reverse the list of children in order to ensure that the leftmost objects get drawn last.
        parent.reverse()

    def layout(self, info:List[ConnectionInfo]) -> List[int]:
        """ Subclasses must choose a row for each child while staying within the given bounds. """
        raise NotImplementedError

    def render(self) -> Tuple[list, list]:
        """ Start the root object drawing on a new canvas and returning the text and node data. """
        return self._root_object.render()


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
        bottom_bound = 3 - (info[0].b_span == 1)
        right_bound = 0
        for child, appearance, col, t_span, b_shift, b_span in info:
            # Advance to the next free row. Move down one more if this child shares columns with the last one.
            row = bottom_bound + (right_bound > col and appearance != TextFlags.SEPARATOR)
            rows.append(row)
            # Advance the bounds by this child's height and width.
            bottom_bound = row + child.height
            right_bound = col + child.width - b_shift
        return rows


class CompressedTextGenerator(TextGenerator):
    """ Cascaded layout that allows drawing to start at the top again under certain conditions
        Since more than one node may occupy the same row, no stroke separators are drawn. """

    def layout(self, info:List[ConnectionInfo]) -> List[int]:
        """ Allocate rows from the top-down as efficiently as possible to keep a rectangular shape. """
        rows = []
        bounds = [-1] * 50
        # Filter out all stroke separators from the info list.
        info[:] = [i for i in info if i.appearance != TextFlags.SEPARATOR]
        # Place nodes into rows using a slot-based system. Each node records which row slot it occupies starting from
        # the top down, and the rightmost column it needs. After that column is passed, the slot becomes free again.
        for child, appearance, col, t_span, b_shift, b_span in info:
            # Index 2 can only be occupied by nodes that attach at the bottom with a single connector.
            row = 3 - (b_span == 1)
            # Search for the next free slot from the top down and place the node there.
            while bounds[row] > col:
                row += 1
            rows.append(row)
            # Make sure other nodes can't be placed directly above, below, or to the right of this one.
            bottom_bound = row + child.height
            right_bound = col + child.width - b_shift
            # Only overwrite the safety margins of other nodes if ours is larger.
            bounds[row - 1] = max(right_bound, bounds[row - 1])
            for i in range(row, bottom_bound):
                bounds[i] = right_bound + 1
            bounds[bottom_bound] = max(right_bound, bounds[bottom_bound])
        return rows
