""" Module for generating a compressed text graph. Nodes are drawn in a rectangular shape as closely as possible. """

from typing import Iterable, List

from spectra_lexer.output.node import OutputNode

from spectra_lexer.output.text.grid import TaggedGrid
from spectra_lexer.output.text.object import TextObject, TextObjectCollection
from spectra_lexer.output.text.symbols import TextConnector, TextNode, TextSeparators, TextConnectorUnmatched, \
    APPEARANCE

class TextGraph(TextObjectCollection):
    """ An aggregate of text objects. Each is drawn at the graph's offset in addition to their own. """

    def __init__(self, node:OutputNode, row:int=0, col:int=0):
        """ Make a list of every text object to display. May include others of this type recursively. """
        super().__init__(row, col, self.layout(node))

    def layout(self, node:OutputNode) -> List[TextObject]:
        """ Subclasses should override this to provide text objects representing the entire node graph. """

    def render(self)-> Iterable[list]:
        """ Render all text objects into standard strings and node grids indexed by position.
            Analyze the bounds of all objects before deciding on the required size. """
        grid = TaggedGrid.blanks(*self.size)
        self.write(grid)
        return grid.compile_strings(), grid.compile_tags()


class CascadedTextGraph(TextGraph):
    """
    Specialized structure for a cascaded plaintext breakdown of steno translations.
    Nodes are drawn in descending order like a waterfall going left-to-right.
    Recursive construction with one line per node means everything fits naturally with no overlap.
    Window space economy is poor (the triangle shape means half the space is wasted off the top).
    Aspect ratio is highly vertical, requiring an awkwardly shaped display window to accommodate.
    """

    def layout(self, node:OutputNode) -> List[TextObject]:
        """ Generate all text objects which make up the graph of a node. """
        appearance = APPEARANCE[node.appearance]
        t_cls = appearance.text
        base = t_cls(0, 0, node)
        objects = [base]
        top_row = row = base.size[0]
        for c in node.children:
            appearance = APPEARANCE[c.appearance]
            c_cls = appearance.connectors
            col = c.attach_start
            if c_cls:
                objects.append(c_cls(top_row, col, c, row - top_row))
            child = CascadedTextGraph(c, row, col)
            row += child.size[0]
            objects.append(child)
        return objects


class CompressedTextGraph(TextGraph):
    """
    Specialized structure for a compressed plaintext breakdown of steno translations.
    This layout is much more compact than cascaded, but can look crowded and confusing.
    Nodes require much more clever placement to avoid ambiguities and wasted space.
    """
