from typing import List, Tuple, TypeVar

from spectra_lexer.text.node import OutputNode

# Symbols used to represent text "containers" in the graph. The middle of each one is replicated to fill gaps.
_CONTAINER_SYMBOLS = {"TOP":    "├─┘",
                      "BOTTOM": "├─┐",
                      "MIDDLE": "|||",
                      "S_BEND": "└─┐",
                      "Z_BEND": "┌─┘",
                      "INV":    "◄═►",
                      "BAD":    "???"}
# Symbols connecting containers together.
_LINE_SYMBOL = "│"
_CORNER_SYMBOL = "┐"
_TEE_SYMBOL = "┬"
# Symbols drawn underneath all others as stroke separators. May be different from the RTFCRE delimiter.
_SEP_SYMBOL = "/"
# Symbols that may not be covered by connectors, such as side split hyphens.
_UNCOVERED_SYMBOLS = {"-"}


def _text_container(length:int, position:str) -> str:
    """ Make a text "container" ├--┐ string based on a left, middle, and right symbol.
        If the container is only a single character wide, use a straight line connector instead. """
    if length < 2:
        return _LINE_SYMBOL
    (left, middle, right) = _CONTAINER_SYMBOLS[position]
    return left + middle * (length - 2) + right


T = TypeVar('_TextOutputLine')
class _TextOutputLine(str):
    """ String wrapper for a single line of text along with node metadata for tooltips.
        The entire object must be immutable, so the node map is a tuple that is only assigned on copy. """

    _node_map: Tuple[OutputNode] = None  # Sequence of node references to indicate which node "owns" each character.

    def _overwrite_copy(self, s:str, src:OutputNode, start:int) -> T:
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

    def with_container(self, src:OutputNode, start:int, length:int, position:str) -> T:
        """ Write a "container" ├--┐ at index <start> and return a copy. """
        return self._overwrite_copy(_text_container(length, position), src, start)

    def with_connector(self, src:OutputNode, start:int) -> T:
        """ Write a vertical line connector at index <start> and return a copy. """
        return self._overwrite_copy(_LINE_SYMBOL, src, start)

    def with_endpiece(self, src:OutputNode, start:int, length:int) -> T:
        """ Write a series of ┬ ending in (or consisting solely of) a ┐ at index <start> and return a copy. """
        extra = [_TEE_SYMBOL] * (length - 1)
        return self._overwrite_copy("".join((*extra, _CORNER_SYMBOL)), src, start)

    def with_node_string(self, src:OutputNode, start:int) -> T:
        """ Write the node's text starting at <start> and return a copy. """
        return self._overwrite_copy(src.text, src, start)

    def replace(self, *args) -> T:
        """ Override the basic string replace function to copy the node map as well. """
        other = _TextOutputLine(super().replace(*args))
        other._node_map = self._node_map
        return other

    def get_node_map(self) -> tuple:
        """ Return the tuple of node references, or an empty tuple if it's still None. """
        return self._node_map or ()


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
                out.append(out.pop().replace(' ', _SEP_SYMBOL))
                continue
            start = child.attach_start
            wp = start + offset
            # Add child recursively.
            _draw_node(out, child, wp, placeholders)
            # Add a line with the bottom connector (using different symbols if the rule uses inversion).
            # If the text leads with a hyphen (uncovered symbol), the connector shouldn't cover it.
            bottom_len = len(child.text)
            if not child.children and wp > 0 and child.text[0] in _UNCOVERED_SYMBOLS:
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
        # If the last child is off the right end (key rules do this), add extensions to connect the placeholder.
        # Tee extensions will connect other children in the rare case of multiple key rules.
        off_end = children[-1].attach_start - len(text)
        if off_end >= 0:
            placeholders = placeholders.with_endpiece(children[-1], offset + len(text), off_end + 1)
    else:
        # If there are no children, it is a base rule. These cases only apply to base rules.
        # If the text leads with a hyphen (right side keys) and there's room, shift it one space to the left.
        if text and text[0] in _UNCOVERED_SYMBOLS and offset > 0:
            offset -= 1
        # If it doesn't overlap anything in the line below it, make that the header and write it there.
        if out and out[-1][offset:offset + len(text)].isspace():
            placeholders = out.pop()
    # The first line contains the text itself. It will overwrite any interfering placeholders.
    out.append(placeholders.with_node_string(src, offset))


def _draw_missing_keys(out:List[_TextOutputLine], src:OutputNode) -> None:
    """ Draw any unmatched keys on the diagram with question marks hanging off. """
    unmatched = _TextOutputLine().with_node_string(src.unmatched_node, 0)
    w = len(unmatched)
    out += [_TextOutputLine(" " * w),
            unmatched.with_container(src.unmatched_node, 0, w, "BAD"),
            unmatched.with_container(src.unmatched_node, 0, w, "MIDDLE"),
            unmatched]


def _generate_text(src:OutputNode) -> List[_TextOutputLine]:
    """ Generate a list of output lines, which are plaintext strings attached
        to data containing the "ownership" of each character by a node. """
    output_lines = []
    # Start from the bottom up adding lines recursively, starting at the left end with no placeholders.
    _draw_node(output_lines, src, 0, _TextOutputLine())
    # Reverse the entire graph to get a top-to-bottom view with the root node on top.
    output_lines.reverse()
    # Draw any unmatched keys last.
    if src.unmatched_node:
        _draw_missing_keys(output_lines, src)
    return output_lines


def generate_text_grid(src:OutputNode) -> Tuple[List[str], List[Tuple[OutputNode]]]:
    """ Main generator for text-based output. Builds a list of plaintext strings from a node tree,
        as well as a grid with additional info about node locations for highlighting support. """
    output_lines = _generate_text(src)
    # Compile all saved node info into a 2D grid indexed by position.
    node_grid = [line.get_node_map() for line in output_lines]
    # Return this with the generated strings, free of the context of any metadata they carry as a subclass.
    return output_lines, node_grid
