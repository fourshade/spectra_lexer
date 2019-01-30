""" Module for higher-level text objects that directly depend on nodes, such as containers and connectors. """

from collections import namedtuple
from functools import lru_cache

from spectra_lexer.output.node import OutputNode
from spectra_lexer.output.text.object import TextGrid, TextObject
from spectra_lexer.output.text.string import TaggedString, TaggedGrid

# Symbols used to represent text "containers" in the graph.
# The "single" symbol is used for length-1 containers, and the "middle" symbol is repeated to fill larger ones.
_ContainerSymbols = namedtuple("_ContainerSymbols", "single sides middle")
_CONTAINER_SYMBOLS_TOP = _ContainerSymbols("│", "├┘", "─")
_CONTAINER_SYMBOLS_BOTTOM = _ContainerSymbols("│", "├┐", "─")
_CONTAINER_SYMBOLS_INV = _ContainerSymbols("│", "◄►", "═")
_CONTAINER_SYMBOLS_END = _ContainerSymbols("┐", "┬┐", "┬")
_CONTAINER_SYMBOLS_MIDDLE = _ContainerSymbols("│", "││", "│")
_CONTAINER_SYMBOLS_QUESTION = _ContainerSymbols("?", "??", "?")
_CONTAINER_SYMBOLS_S_BEND = _ContainerSymbols("│", "└┐", "─")
_CONTAINER_SYMBOLS_Z_BEND = _ContainerSymbols("│", "┌┘", "─")
# Singular symbol connecting containers together.
_LINE_SYMBOL = "│"
# Symbol drawn underneath all others as a stroke separator. May be different from the RTFCRE delimiter.
_SEP_SYMBOL = "/"


@lru_cache(maxsize=None)
def _text_container(length:int, symbols:namedtuple) -> str:
    """ Return a variable-length "container" ├----┐ string based on a set of construction symbols. """
    # If the container is only a single character wide, use the unique "single" symbol.
    if length < 2:
        return symbols.single
    # If the container is two characters wide, use just the left and right symbols.
    sides = symbols.sides
    if length == 2:
        return sides
    # Otherwise put the left and right symbols at the ends and repeat the middle one inside to cover the rest.
    (left, right) = sides
    middle = symbols.middle * (length - 2)
    return left + middle + right


class TextNode(TextGrid):
    """ List of text lines that form a node and its attachments one character in each direction.
        Sections of text belonging to a single node are added with positions depending on the node attributes. """

    def __init__(self, row:int, col:int, node:OutputNode) -> None:
        """ Default implementation draws the node and its basic end attachments, shifted for hyphens. """
        # TODO: Fix shifting when col=0
        shift = node.bottom_start
        super().__init__(row, col - shift)
        if node.parent:
            self._add_bottom_container(node, shift)
        self._add_node_string(node)
        if node.children:
            self._add_top_containers(node)

    def order(self):
        """ Nodes are important. They should be drawn over top of other objects. """
        return 1

    def _add_top_containers(self, node:OutputNode, _blanks=TaggedString.blanks) -> None:
        """ Write top "containers" ├--┘ for child nodes on a new line with parent <node> at index <start>. """
        top = _blanks(len(node.text))
        self.append(top)
        for c in node.children:
            if not (c.is_separator or c.is_unmatched):
                top.write(_text_container(c.attach_length, _CONTAINER_SYMBOLS_TOP), c, c.attach_start)

    def _add_node_string(self, node:OutputNode, _new=TaggedString.from_string) -> None:
        """ Add a new line with the node's text starting at <start>.
            If any children of this node hang off the right edge, write an "endpiece" to connect them. """
        n_text = _new(node.text, node)
        self.append(n_text)
        children = node.children
        if children:
            last_child = children[-1]
            text_len = len(node.text)
            off_end = last_child.attach_start - text_len
            if off_end >= 0:
                n_text.write(_text_container(off_end + 1, _CONTAINER_SYMBOLS_END), last_child, text_len)

    def _add_bottom_container(self, node:OutputNode, start:int=0, _new=TaggedString.from_string) -> None:
        """ Add a bottom "container" ├--┐ for a child node with bottom attach point at index <start>.
            Inversions of steno order are drawn differently, and starting hyphens will not be covered. """
        container_type = _CONTAINER_SYMBOLS_INV if node.is_inversion else _CONTAINER_SYMBOLS_BOTTOM
        bottom = _new(_text_container(node.bottom_length, container_type), node, start)
        self.append(bottom)


class TextGridUnmatched(TextNode):
    """ A list of unmatched keys with question marks hanging off. """

    def _add_bottom_container(self, node:OutputNode, start:int=0, _new=TaggedString.from_string) -> None:
        w = node.bottom_length
        self.extend([_new(_text_container(w, _CONTAINER_SYMBOLS_QUESTION), node, start),
                     _new(_text_container(w, _CONTAINER_SYMBOLS_MIDDLE), node, start)])


class TextConnector(TextObject):
    """ A vertical connector joining two nodes. """

    node: OutputNode  # Child attached by the connector.
    length: int       # Rows spanned by the connector.

    def __init__(self, row:int, col:int, node:OutputNode, length:int=1):
        super().__init__(row, col)
        self.node = node
        self.length = length

    def bounds(self):
        return self.row + self.length, self.col

    def write(self, canvas:TaggedGrid) -> None:
        """ Draw a vertical connector running down multiple rows. """
        canvas.write_column(_LINE_SYMBOL * self.length, self.node, self.row, self.col)


class TextSeparators(TextObject):
    """ A row of stroke separators. These are not connected to anything, nor is their ownership displayed. """

    def order(self):
        """ Stroke separators should appear underneath most other objects. """
        return -1

    def write(self, canvas:TaggedGrid) -> None:
        """ Replace every space in the row with unowned separators. """
        canvas[self.row].str_op(str.replace, " ", _SEP_SYMBOL)

