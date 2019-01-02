from __future__ import annotations
from typing import List, Tuple

from spectra_lexer.keys import KEY_SEP, KEY_SPLIT
from spectra_lexer.node import OutputNode

# Symbols used to represent text "containers" in the graph. The middle of each one is replicated to fill gaps.
_CONTAINER_SYMBOLS = {"TOP":    "├─┘",
                      "BOTTOM": "├─┐",
                      "S_BEND": "└─┐",
                      "Z_BEND": "┌─┘",
                      "INV":    "◄═►"}
# Symbols connecting containers together.
_LINE_SYMBOL = "│"
_CORNER_SYMBOL = "┐"


def _text_container(length:int, position:str) -> str:
    """ Make a text "container" ├--┐ string based on a left, middle, and right symbol.
        If the container is only a single character wide, use a straight line connector instead. """
    if length < 2:
        return _LINE_SYMBOL
    (left, middle, right) = _CONTAINER_SYMBOLS[position]
    return left + middle * (length - 2) + right


class _TextOutputLine(str):
    """ String wrapper for a single line of text along with node metadata for tooltips.
        The entire object must be immutable, so the node map is a tuple that is only assigned on copy. """

    _node_map: Tuple[OutputNode] = None  # Sequence of node references to indicate which node "owns" each character.

    def _overwrite_copy(self, s:str, src:OutputNode, start:int) -> _TextOutputLine:
        """ Make a copy of this object with the string <s> overwriting characters starting
            at <start>, padding with spaces if necessary and writing to the node map as well. """
        end = start + len(s)
        other = _TextOutputLine(self.rjust(start)[:start] + s + self[end:])
        if src is not None:
            nmap = self._node_map
            if nmap is None:
                nmap = (None,) * max(start, len(self))
            other._node_map = nmap[:start] + (src,) * len(s) + nmap[end:]
        return other

    def with_container(self, src:OutputNode, start:int, length:int, position:str) -> _TextOutputLine:
        """ Write a "container" ├--┐ at index <start> and return a copy. """
        return self._overwrite_copy(_text_container(length, position), src, start)

    def with_connector(self, src:OutputNode, start:int) -> _TextOutputLine:
        """ Write a vertical line connector at index <start> and return a copy. """
        return self._overwrite_copy(_LINE_SYMBOL, src, start)

    def with_corner(self, src:OutputNode, start:int) -> _TextOutputLine:
        """ Write a corner character at index <start> and return a copy. """
        return self._overwrite_copy(_CORNER_SYMBOL, src, start)

    def with_node_string(self, src:OutputNode, start:int) -> _TextOutputLine:
        """ Write the node's text starting at <start> and return a copy. """
        return self._overwrite_copy(src.text, src, start)

    def replace(self, *args) -> _TextOutputLine:
        """ Override the basic string replace function to copy the node map as well. """
        other = _TextOutputLine(super().replace(*args))
        other._node_map = self._node_map
        return other

    def get_node_map(self) -> tuple:
        """ Return the tuple of node references, or an empty tuple if it's still None. """
        return self._node_map or ()


def generate_text(src:OutputNode) -> Tuple[List[str], List[Tuple[OutputNode]]]:
    """ Main generator for output text. Builds a list of plaintext strings from a node tree,
        as well as a grid with additional info about node locations for highlighting support. """
    if src.children:
        # Use the helper function to add lines recursively, starting at the left end with no placeholders.
        output_lines = []
        _draw_node(output_lines, src, 0, _TextOutputLine())
        output_lines.reverse()
    else:
        # A root node by itself means we didn't find any complete matches with the lexer.
        output_lines = _incomplete_graph(src)
    # Return the generated strings, free of the context of any metadata they carry as a subclass.
    # Compile all saved node info into a 2D grid indexed by position.
    node_grid = [line.get_node_map() for line in output_lines]
    return output_lines, node_grid


def _draw_node(out:List[_TextOutputLine], src:OutputNode, offset:int, placeholders:_TextOutputLine) -> None:
    """ Add lines of vertical cascaded plaintext to the string list. They are added recursively in reverse order.
        This means that the order must be reversed back by the caller at the top level. """
    text = src.text
    children = src.children
    # If there are children, start adding results in reverse order building up.
    if children:
        top = placeholders
        for child in reversed(children):
            if child.is_separator:
                # If it's a separator, add slashes behind the previous line and do nothing else.
                out.append(out.pop().replace(' ', KEY_SEP))
            else:
                start = child.attach_start
                wp = start + offset
                # Add child recursively.
                _draw_node(out, child, wp, placeholders)
                # Add a line with the bottom connector (using different symbols if the rule uses inversion).
                # If the text leads with a hyphen, the connector shouldn't cover it.
                bottom_len = len(child.text)
                if not child.children and wp > 0 and child.text[0] == KEY_SPLIT:
                    bottom_len -= 1
                bottom_container_type = "INV" if child.is_inversion else "BOTTOM"
                out.append(placeholders.with_container(child, wp, bottom_len, bottom_container_type))
                # Place this child's top connector on the holding container.
                top = top.with_container(child, wp, child.attach_length, "TOP")
                # Add a permanent connector line to the placeholders.
                placeholders = placeholders.with_connector(child, wp)
        # Destroy the last line if the first child had one character (i.e. connection is a line).
        if out[-1][offset] == _LINE_SYMBOL:
            out.pop()
        # Add the finished set of top connectors.
        out.append(top)
        # If the last child is off the right end (key rules do this), add a corner to connect the placeholder.
        # TODO: handle case with multiple key rules?
        if children[-1].attach_start == len(text):
            placeholders = placeholders.with_corner(children[-1], offset + len(text))
    else:
        # If there are no children, it is a base rule. These cases only apply to base rules.
        # If the text leads with a hyphen (right side keys) and there's room, shift it one space to the left.
        if text and text[0] == KEY_SPLIT and offset > 0:
            offset -= 1
        # If it doesn't overlap anything in the line below it, make that the header and write it there.
        if out and out[-1][offset:offset + len(text)].isspace():
            placeholders = out.pop()
    # The first line contains the text itself. It will overwrite any interfering placeholders.
    out.append(placeholders.with_node_string(src, offset))


def _incomplete_graph(src:OutputNode) -> List[_TextOutputLine]:
    """ Draw a graph with the base node along with lines that show the lexer's failure to make a good guess. """
    word = src.text
    connectors = "".join([_LINE_SYMBOL if c.isalnum() else " " for c in word])
    return [_TextOutputLine().with_node_string(src, 0),
            _TextOutputLine(connectors),
            _TextOutputLine(connectors.replace(_LINE_SYMBOL, "?"))]
