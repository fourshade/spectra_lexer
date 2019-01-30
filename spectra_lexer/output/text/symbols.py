""" Module for higher-level text objects that directly depend on nodes, such as containers and connectors. """

from collections import namedtuple
from functools import lru_cache

from spectra_lexer.output.node import OutputNode
from spectra_lexer.output.text.grid import TaggedGrid
from spectra_lexer.output.text.object import TextObject, TextGrid
from spectra_lexer.rules import OutputFlags

# Symbols used to represent text patterns in the graph.
# The "single" symbol is used for length-1 containers, and the "middle" symbol is repeated to fill larger ones.
_GraphSymbols = namedtuple("_GraphSymbols", "single sides middle")
_GRAPH_SYMBOLS_TOP = _GraphSymbols("│", "├┘", "─")
_GRAPH_SYMBOLS_BOTTOM = _GraphSymbols("│", "├┐", "─")
_GRAPH_SYMBOLS_INV = _GraphSymbols("│", "◄►", "═")
_GRAPH_SYMBOLS_END = _GraphSymbols("┐", "┬┐", "┬")
_GRAPH_SYMBOLS_BAD_MIDDLE = _GraphSymbols("|", "||", "|")
_GRAPH_SYMBOLS_BAD_END = _GraphSymbols("?", "??", "?")
_GRAPH_SYMBOLS_CONNECTORS = _GraphSymbols("│", "││", "│")
_GRAPH_SYMBOLS_SEPARATORS = _GraphSymbols("/", "//", "/")
# _GRAPH_SYMBOLS_S_BEND = _GraphSymbols("│", "└┐", "─")
# _GRAPH_SYMBOLS_Z_BEND = _GraphSymbols("│", "┌┘", "─")


@lru_cache(maxsize=None)
def _pattern(length:int, symbols:namedtuple) -> str:
    """ Return a variable-length pattern string with unique ends based on a set of construction symbols. """
    # If the pattern is only a single character wide, use the unique "single" symbol.
    if length < 2:
        return symbols.single
    # If the pattern is two characters wide, use just the left and right symbols.
    sides = symbols.sides
    if length == 2:
        return sides
    # Otherwise put the left and right symbols at the ends and repeat the middle one inside to cover the rest.
    (left, right) = sides
    middle = symbols.middle * (length - 2)
    return left + middle + right


class TextNode(TextGrid):
    """ Grid of text lines that form a node and its attachments one character in each direction.
        Sections of text belonging to a single node are added with positions depending on the node attributes. """

    # Nodes are important. They should be drawn over top of other objects.
    ORDER = 5

    def __init__(self, row:int, col:int, node:OutputNode) -> None:
        """ Default implementation draws the node and its basic end attachments, shifted for hyphens. """
        # TODO: Fix shifting when col=0
        shift = node.bottom_start
        row_count = 1 + bool(node.parent) + bool(node.children)
        col_count = len(node.text)
        super().__init__(row, col - shift, row_count, col_count)
        if node.parent:
            self._add_bottom_container(node, row, shift)
            row += 1
        self._add_node_text(node, row)
        row += 1
        if node.children:
            self._add_top_containers(node, row)

    def _add_top_containers(self, node:OutputNode, row:int=0) -> None:
        """ Add top "containers" ├--┘ for child nodes with parent <node> starting at column 0. """
        for c in node.children:
            pattern_type = APPEARANCE[c.appearance].top
            if pattern_type:
                self.grid.write_row(_pattern(c.attach_length, pattern_type), c, row, c.attach_start)

    def _add_node_text(self, node:OutputNode, row:int=0) -> None:
        """ Add a new line with the node's text starting at column 0. If any children of this
            node hang off the right edge, write an "endpiece" on the same line to connect them. """
        self.grid.write_row(node.text, node, row)
        children = node.children
        if children:
            last_child = children[-1]
            text_len = len(node.text)
            off_end = last_child.attach_start - text_len
            if off_end >= 0:
                self.grid.write_row(_pattern(off_end + 1, _GRAPH_SYMBOLS_END), last_child, row, text_len)

    def _add_bottom_container(self, node:OutputNode, row:int=0, shift:int=0) -> None:
        """ Add a bottom "container" ├--┐ for a child <node> with bottom attach point at column 0.
            The container may be moved <shift> characters to the right to avoid starting hyphens. """
        pattern_type = APPEARANCE[node.appearance].bottom
        if pattern_type:
            self.grid.write_row(_pattern(node.bottom_length, pattern_type), node, row, shift)


class TextSeparators(TextObject):
    """ A row of stroke separators. These are not connected to anything, nor is their ownership displayed. """

    # Stroke separators fill in any gaps, so they should be drawn last.
    ORDER = 10

    def __init__(self, row:int, *args):
        """ A connector spans multiple rows, but is only one character wide. """
        super().__init__(row, 0)

    def write(self, canvas:TaggedGrid, row:int=0, col:int=0) -> None:
        """ Replace every space in the row with unowned separators. """
        y, x = self.offset
        canvas.row_str_op(row + y, str.replace, " ", _GRAPH_SYMBOLS_SEPARATORS.single)


class TextConnector(TextObject):
    """ A vertical connector joining two nodes. """

    # Connectors should appear underneath most other objects.
    ORDER = -1

    string: str       # String of connectors characters (usually just vertical lines).
    node: OutputNode  # Child node attached by the connector.

    def __init__(self, row:int, col:int, node:OutputNode, length:int=1):
        """ A connector spans multiple rows, but is only one character wide. """
        super().__init__(row, col, length, 1)
        self.string = _pattern(length, _GRAPH_SYMBOLS_CONNECTORS)
        self.node = node

    def write(self, canvas:TaggedGrid, row:int=0, col:int=0) -> None:
        """ Draw a vertical connector running down multiple rows. """
        y, x = self.offset
        canvas.write_column(self.string, self.node, row + y, col + x)


class TextConnectorUnmatched(TextGrid):
    """ Graphical element for connecting unmatched keys to the remaining letters. """

    # Mystery connectors should appear under even regular ones.
    ORDER = -5

    def __init__(self, row:int, col:int, node:OutputNode, length:int=1) -> None:
        length = max(5, length + 2)
        cols_upper = node.attach_length
        cols_lower = node.bottom_length
        cols_max = max(cols_upper, cols_lower)
        super().__init__(row, col, length, cols_max)
        start_c = _pattern(cols_upper, _GRAPH_SYMBOLS_BAD_MIDDLE)
        start_q = _pattern(cols_upper, _GRAPH_SYMBOLS_BAD_END)
        end_q = _pattern(cols_lower, _GRAPH_SYMBOLS_BAD_END)
        # Run connectors and finish with a question mark just before the gap would close.
        for r in range(length - 5):
            self.grid.write_row(start_c, node, r)
        self.grid.write_row(start_q, node, length - 5)
        # After the gap, cap off the node text with question marks.
        self.grid.write_row(end_q, node, length - 1)


# Flags for rules with special display properties and the appearance classes/patterns of each.
NodeAppearance = namedtuple("_NodeAppearance", "text bottom top connectors")
APPEARANCE =        {None: NodeAppearance(TextElementNode, _GRAPH_SYMBOLS_BOTTOM, _GRAPH_SYMBOLS_TOP, TextElementConnector),
                     OutputFlags.SEPARATOR: NodeAppearance(TextElementSeparators, None, None, None),
                     OutputFlags.UNMATCHED: NodeAppearance(TextElementNode, *([_GRAPH_SYMBOLS_BAD_MIDDLE] * 2), TextElementConnectorUnmatched),
                     OutputFlags.INVERSION: NodeAppearance(TextElementNode, _GRAPH_SYMBOLS_INV, _GRAPH_SYMBOLS_TOP, TextElementConnector)}
