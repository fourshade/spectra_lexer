""" Module controlling the layout of text graphs, including construction and placement of all drawable objects. """

from operator import attrgetter
from typing import Tuple

from spectra_lexer.graph.text.layout.object import ObjectNode, ObjectNodeUnmatched
from spectra_lexer.graph.text.layout.pattern import *
from spectra_lexer.graph.text.node import TextFlags, TextNode
from spectra_lexer.rules import StenoRule

# Aoppearance flag table with custom object and pattern constructor types.
_FLAG_APPEARANCE = {TextFlags.SEPARATOR:   (ObjectNode,          PatternSeparators),
                    TextFlags.UNMATCHED:   (ObjectNodeUnmatched, PatternUnmatched),
                    TextFlags.INVERSION:   (ObjectNode,          PatternInversion),
                    TextFlags.ROOT:        (ObjectNode,          Pattern),
                    TextFlags.BRANCH:      (ObjectNode,          Pattern),
                    TextFlags.LEAF:        (ObjectNode,          Pattern)}

# Convenience function to get all relevant layout attributes from a child node object.
_NODE_ATTRS = attrgetter("object", "attach_start", "attach_length", "bottom_start", "bottom_length")


class TextLayout(TextNode):
    """ A node containing an aggregate of drawable text objects. Subclasses lay out the children however they want.
        render() produces the text lines and child objects references making it up. """

    object: ObjectNode  # Main container for drawable objects.

    def __init__(self, rule:StenoRule, *args):
        """ Create a node from a rule and make a list of text objects to display for it.
            Because of recursion, all child nodes and text objects will be done after the super call. """
        super().__init__(rule, *args)
        # Look up the type and pattern for this node based on the appearance flag and create the object.
        obj, pattern = _FLAG_APPEARANCE[self.appearance]
        self.object = obj(self.text, self, pattern)
        # If there are children, start adding them according to the subclass layout.
        if self.children:
            self.layout_children()

    def layout_children(self) -> None:
        """ Subclasses are responsible for placing and attaching child objects here. """
        raise NotImplementedError

    def render(self) -> Tuple[list, list]:
        return self.object.render()


class CascadedTextLayout(TextLayout):
    """
    Specialized structure for a cascaded plaintext breakdown of steno translations.
    Nodes are drawn in descending order like a waterfall going left-to-right.
    Recursive construction with one line per node means everything fits naturally with no overlap.
    Window space economy is poor (the triangle shape means half the space is wasted off the top).
    Aspect ratio is highly vertical, requiring an awkwardly shaped display window to accommodate.
    """

    def layout_children(self) -> None:
        """ Add children from the top-down with spacing according to their finished size. """
        parent = self.object
        c_attrs = list(map(_NODE_ATTRS, self.children))
        # Start the first child three rows down, or only two if it attaches at the bottom with a single connector.
        b_span = c_attrs[0][4]
        row = 3 - (b_span == 1)
        prev_right = 0
        # There are four coordinates of interest to look up when attaching a child node.
        # They are: main attach column, top attachment length, bottom left-shift, and bottom attachment length.
        for child, col, t_span, b_shift, b_span in c_attrs:
            # Advance the row count by one more if this child shares columns with the last one.
            row += (prev_right > col and child.width > 0)
            # Draw the connectors on the parent with the bottom-left corner at (row, col).
            child.draw_connectors(parent, col, t_span, row, col, b_span)
            # Actually attach the child at (row, col - shift) to account for hyphens.
            child.attach(parent, row, col - b_shift)
            # Advance the row count by the finished child's height.
            row += child.height
            prev_right = col + child.width - b_shift
        # Reverse the list of children in order to ensure that the leftmost objects get drawn last.
        parent.reverse()


class CompressedTextLayout(TextLayout):
    """
    Specialized structure for a compressed plaintext breakdown of steno translations.
    This layout is much more compact than cascaded, but can look crowded and confusing.
    Nodes require much more clever placement to avoid ambiguities and wasted space.
    """

    def layout_children(self) -> None:
        return
