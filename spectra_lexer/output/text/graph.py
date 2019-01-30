""" Module for general text graph drawing and basic data structures. """

from collections import namedtuple
from functools import lru_cache
from typing import Iterable, List

from spectra_lexer.output.node import OutputNode, OutputTree


# Symbols used to represent text "containers" in the graph.
# The "single" symbol is used for length-1 containers, and the "middle" symbol is repeated to fill larger ones.
_ContainerSymbols = namedtuple("_ContainerSymbols", "single sides middle")
_CONTAINER_SYMBOLS_TOP = _ContainerSymbols("│", "├┘", "─")
_CONTAINER_SYMBOLS_BOTTOM = _ContainerSymbols("│", "├┐", "─")
_CONTAINER_SYMBOLS_INV = _ContainerSymbols("│", "◄►", "═")
_CONTAINER_SYMBOLS_S_BEND = _ContainerSymbols("│", "└┐", "─")
_CONTAINER_SYMBOLS_Z_BEND = _ContainerSymbols("│", "┌┘", "─")
# Singular symbols connecting containers together.
_LINE_SYMBOL = "│"
_CORNER_SYMBOL = "┐"
_TEE_SYMBOL = "┬"
_UNMATCHED_SYMBOL = "?"
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


@lru_cache(maxsize=None)
def _text_endpiece(length:int) -> str:
    """ Return a corner piece ┐ preceded by repeated ┬ characters to fill the rest of the length. """
    return (_TEE_SYMBOL * (length - 1)) + _CORNER_SYMBOL


class TaggedString(list):
    """ A mutable string-like structure that has a metadata tag object associated with each character.
        For performance, the implementation is low-level: a list with alternating characters and tags. """

    def write(self, s:str, tag:object, start:int=0, _len=len) -> None:
        """ Overwrite characters with <s> and tags with <tag> starting at <start>.
            The most performance-critical method in graphing, called hundreds of times per frame.
            Avoid method call overhead by inlining everything and using slice assignment over list methods. """
        start *= 2
        length = _len(s) * 2
        under = start - _len(self)
        if under > 0:
            self.extend([" ", None] * (under // 2))
        end = start + length
        self[start:end] = [tag] * length
        self[start:end:2] = s

    def write_line(self, line:list, start:int=0, _len=len) -> None:
        """ Write an entire line of tagged characters over this one starting at <start>. """
        start *= 2
        under = start - _len(self)
        if under > 0:
            self.extend([" ", None] * (under // 2))
        self[start:start + _len(line)] = line

    def replace(self, s:str, rep:str) -> None:
        """ Do a string replace operation without altering any tags. """
        self[::2] = [rep if c == s else c for c in self[::2]]

    def data(self, _join="".join) -> tuple:
        """ De-interleave the string and tag data to construct the graph. """
        return _join(self[::2]), self[1::2]


class TextGraphLine(TaggedString):
    """ A mutable line of text with node ownership metadata attached to each character. There is no line break.
        Sections of text belonging to a single node are added with a position depending on the node attributes. """

    @classmethod
    def filler(cls, length:int, fill:str=" ", node:OutputNode=None):
        """ Make a new text line consisting of repeated characters (spaces by default) and node references. """
        self = cls()
        self.write(fill * length, node)
        return self

    def add_top_container(self, node:OutputNode, start:int) -> None:
        """ Write a top "container" ├--┘ for a child node with top attach point at index <start>. """
        self.write(_text_container(node.attach_length, _CONTAINER_SYMBOLS_TOP), node, start)

    def add_connector(self, node:OutputNode, start:int) -> None:
        """ Write a vertical connector connecting a child node with attach line at index <start>. """
        self.write(_LINE_SYMBOL, node, start)

    def add_bottom_container(self, node:OutputNode, start:int) -> None:
        """ Write a bottom "container" ├--┐ for a child node with bottom attach point at index <start>.
            Inversions of steno order are drawn differently, and starting hyphens will not be covered. """
        container_type = _CONTAINER_SYMBOLS_INV if node.is_inversion else _CONTAINER_SYMBOLS_BOTTOM
        self.write(_text_container(node.bottom_length, container_type), node, start)

    def add_node_string(self, node:OutputNode, start:int) -> None:
        """ Write the node's text starting at <start>, shifting to account for hyphens unless there's no room.
            If any children of this node hang off the right edge, write an "endpiece" to connect them. """
        if start >= node.bottom_start:
            start -= node.bottom_start
        self.write(node.text, node, start)
        children = node.children
        if children:
            last_child = children[-1]
            text_len = len(node.text)
            off_end = last_child.attach_start - text_len
            if off_end >= 0:
                self.write(_text_endpiece(off_end + 1), last_child, start + text_len)

    def add_separators(self) -> None:
        """ Stroke separators are not connected like other nodes. For them, just write slashes behind the line. """
        self.replace(' ', _SEP_SYMBOL)


class TextGraphBlock(List[TextGraphLine]):
    """ List of output text structures that form a full 2D text graph when concatenated with newlines
        as well as a grid with additional info about node locations for highlighting support. """

    def copy(self) -> List[TextGraphLine]:
        """ Copy the text line lists one level deep and put them in a new block. """
        return self.__class__(map(TextGraphLine, self))

    def write_block(self, node:List[TextGraphLine], start_row:int=0, start_col:int=0) -> None:
        """ Copy the contents of one text block to this one at the given offset.
            If there aren't enough rows, pad with all-space rows up to the column start position. """
        rows_over = start_row + len(node) - len(self)
        if rows_over > 0:
            self.extend(TextGraphLine.filler(start_row) for _ in range(rows_over))
        for i, line in enumerate(node, start_row):
            self[i].write_line(line, start_col)


class TextGraph(TextGraphBlock):
    """ A complete text graph with node data created recursively from a root node. """

    def __init__(self, tree:OutputTree):
        """ Main generator for text-based output. Builds all structures on initialization. """
        super().__init__()
        # Draw the root node, which contains everything else
        self.draw(tree)
        # Draw any unmatched keys last.
        if tree.unmatched_node:
            self.draw_unmatched(tree.unmatched_node)

    def draw(self, node:OutputNode) -> None:
        """ Default implementation just draws the root node by itself on a line. Subclasses should override this. """
        self.append(TextGraphLine.filler(1, node.text, node))

    def draw_unmatched(self, node:OutputNode) -> None:
        """ Draw unmatched keys on new lines at the end of the graph with question marks hanging off. """
        w = len(node.text)
        self.extend([TextGraphLine.filler(w),
                     TextGraphLine.filler(w, _UNMATCHED_SYMBOL, node),
                     TextGraphLine.filler(w, _LINE_SYMBOL, node),
                     TextGraphLine.filler(1, node.text, node)])

    def compile_data(self)-> Iterable[tuple]:
        # Compile all text lines and saved node info into 2D grids indexed by position.
        return zip(*map(TextGraphLine.data, self))
