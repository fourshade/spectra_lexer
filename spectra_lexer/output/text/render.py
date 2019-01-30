""" Module for generating a compressed text graph. Nodes are drawn in a rectangular shape as closely as possible. """

from typing import Iterable

from spectra_lexer.output.node import OutputTree, OutputNode
from spectra_lexer.output.text.object import TextObjectCollection
from spectra_lexer.output.text.node import TextGridUnmatched, TextNode, TextConnector, TextSeparators
from spectra_lexer.output.text.string import TaggedGrid


class TextRenderer(TextObjectCollection):
    """ A complete text graph with node data created recursively from a root node. """

    def __init__(self, node:OutputNode):
        """ Main generator for text-based output. Builds all structures on initialization. """
        super().__init__()
        self.draw(node)

    def draw(self, node:OutputNode) -> None:
        """ Subclasses should override this to add text objects representing the entire node graph. """

    def render(self)-> Iterable[list]:
        """ Render all text objects into standard strings and node grids indexed by position.
            Analyze the bounds of all objects before deciding on the required size. """
        grid = TaggedGrid.blanks(*self.bounds())
        self.write(grid)
        return grid.compile_strings(), grid.compile_tags()


class CascadedTextRenderer(TextRenderer):
    """
    Specialized structure for a cascaded plaintext breakdown of steno translations.
    Nodes are drawn in descending order like a waterfall going left-to-right.
    Recursive construction with one line per node means everything fits naturally with no overlap.
    Window space economy is poor (the triangle shape means half the space is wasted off the top).
    Aspect ratio is highly vertical, requiring an awkwardly shaped display window to accommodate.
    """

    def draw(self, node:OutputNode, row:int=0, col:int=0) -> int:
        """ Add a node from scratch. """
        obj = TextNode(row, col, node)
        self.append(obj)
        row += len(obj)
        top_row = row
        for c in node.children:
            if c.is_separator:
                self.append(TextSeparators(row))
                continue
            offset = c.attach_start + col
            if c.is_unmatched:
                self.append(TextGridUnmatched(row, offset, c))
                continue
            self.append(TextConnector(top_row, offset, c, row - top_row))
            row = self.draw(c, row, offset)
        return row


class CompressedTextRenderer(TextRenderer):
    """
    Specialized structure for a compressed plaintext breakdown of steno translations.
    This layout is much more compact than cascaded, but can look crowded and confusing.
    Nodes require much more clever placement to avoid ambiguities and wasted space.
    """
