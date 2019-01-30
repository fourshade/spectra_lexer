""" Module controlling the layout of text graphs, including construction and placement of all drawable objects. """

from collections import defaultdict
from operator import attrgetter
from typing import Iterable

from spectra_lexer.graph.text.layout.object import *
from spectra_lexer.graph.text.node import TextNode
from spectra_lexer.rules import StenoRule

# Output flag lookup table with custom properties of how to display a node
# Maps flags (or lack thereof) to text object constructors, with a default appearance if there are none.
_NODE_APPEARANCE = defaultdict(lambda: ObjectNode,
                               {TextNode.FLAG_SEPARATOR: ObjectSeparators,
                                TextNode.FLAG_UNMATCHED: ObjectNodeUnmatched,
                                TextNode.FLAG_INVERSION: ObjectNodeInversion})

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
        # Look up the type required to create a drawable object for this node based on the first output flag (if any).
        base_tp = _NODE_APPEARANCE[self.flags and next(iter(self.flags))]
        self.object = base_tp(self.text, self)
        # If there are children, start adding them according to their subclass layout.
        if self.children:
            self.layout_children()

    def layout_children(self):
        """ Subclasses are responsible for placing and attaching child objects here. """
        raise NotImplementedError

    def render(self, row:int=0, col:int=0) -> Iterable[list]:
        """ Render all text objects onto a grid of the minimum required size. Try again with a larger one if it fails.
            Return a list of standard strings and a grid with node references indexed by position. """
        s = row + col
        canvas = Canvas.blanks(self.object.height + s, self.object.width + s)
        try:
            self.object.write(canvas, row, col)
        except ValueError:
            return self.render(row + bool(s), col + (not s))
        return canvas.compile_strings(), canvas.compile_tags()


class CascadedTextLayout(TextLayout):
    """
    Specialized structure for a cascaded plaintext breakdown of steno translations.
    Nodes are drawn in descending order like a waterfall going left-to-right.
    Recursive construction with one line per node means everything fits naturally with no overlap.
    Window space economy is poor (the triangle shape means half the space is wasted off the top).
    Aspect ratio is highly vertical, requiring an awkwardly shaped display window to accommodate.
    """

    def layout_children(self):
        """ Add children from the top-down with spacing according to their finished size. """
        row = 3
        parent = self.object
        c_attrs = map(_NODE_ATTRS, self.children)
        # There are four coordinates of interest to look up when attaching a child node.
        # They are: main attach column, top attachment length, bottom left-shift, and bottom attachment length.
        for child, col, t_span, b_shift, b_span in c_attrs:
            # Draw the connectors on the parent with the bottom-left corner at (row, col).
            child.draw_connectors(parent, col, t_span, row, col, b_span)
            # Actually attach the child at (row, col - shift) to account for hyphens.
            child.attach(parent, row, col - b_shift)
            # Advance the row count by the child's height, plus one more if it will overlap the next child.
            row += child.height + (t_span < child.width)
        # Reverse the list of children in order to ensure that the leftmost objects get drawn last.
        parent.reverse()


class CompressedTextLayout(TextLayout):
    """
    Specialized structure for a compressed plaintext breakdown of steno translations.
    This layout is much more compact than cascaded, but can look crowded and confusing.
    Nodes require much more clever placement to avoid ambiguities and wasted space.
    """

    def layout_children(self):
        pass
