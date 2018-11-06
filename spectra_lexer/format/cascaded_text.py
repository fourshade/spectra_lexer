from collections import defaultdict

from typing import Dict, List, NamedTuple, Sequence, Tuple, Union

from spectra_lexer.keys import KEY_SPLIT
from spectra_lexer.output import OutputNode

# Symbols used to represent text "containers" in the graph. The middle of each one is replicated to fill gaps.
_CONTAINER_SYMBOLS = {"TOP":    "├─┘",
                      "BOTTOM": "├─┐",
                      "INV":    "◄═►"}
# Symbols connecting containers together.
_LINE_SYMBOL = "│"
_CORNER_SYMBOL = "┐"
# Sets of various drawing symbols for quick membership testing.
_LINE_CHARACTER_SET = {_LINE_SYMBOL, " "}
_CONTAINER_CHARACTER_SET = {char for s in _CONTAINER_SYMBOLS.values() for char in s}
_GRAPH_CHARACTER_SET = _CONTAINER_CHARACTER_SET | {_LINE_SYMBOL, _CORNER_SYMBOL, " "}


class TextFormatInfo(NamedTuple):
    """ Data structure representing a formatting action over a single line of text. """
    row: int                      # Which row in the text this action affects.
    start: int                    # Starting character/column to format (inclusive)
    end: int                      # Ending character/column to format (exclusive)
    color: Tuple[int, int, int]   # RGB 0-255 color tuple for this range's highlighting
    bold: bool                    # If true, apply boldface to this range of text.


class TextRuleInfo(NamedTuple):
    """
    Data structure returned by get_info_at. For a given rule that is displayed somewhere in the text,
    contains its steno keys and description as well as a list of locations in the text that correspond
    to it (and how it should be formatted when the mouse goes over it).
    """
    keys: str                          # Steno keys to be displayed on the diagram.
    description: str                   # Text description of the rule highlighted.
    format_info: List[TextFormatInfo]  # Areas to place formatting in and what to do.


class _TextOutputLine(str):
    """ String wrapper for a single line of text along with node metadata for tooltips.
        The entire object must be immutable, so the node map is a tuple that is only assigned on copy. """

    _node_map: Tuple[OutputNode] = None  # Sequence of node references to indicate which node "owns" each character.

    def _overwrite_copy(self, src:OutputNode, s:str, start:int) -> __qualname__:
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

    def with_container(self, src:OutputNode, start:int, length:int, position:str="TOP") -> __qualname__:
        """ Place a vertical "container" ├--┐ based on a left, middle, and right symbol and return a copy.
            If the container is only a single character wide, use a straight line connector instead. """
        if length < 2:
            s = _LINE_SYMBOL
        else:
            (left, middle, right) = _CONTAINER_SYMBOLS[position]
            s = left + middle * (length - 2) + right
        return self._overwrite_copy(src, s, start)

    def with_connector(self, src: OutputNode, start: int) -> __qualname__:
        """ Write a vertical line connector at index <start> and return a copy. """
        return self._overwrite_copy(src, _LINE_SYMBOL, start)

    def with_corner(self, src:OutputNode, start:int) -> __qualname__:
        """ Write a corner character at index <start> and return a copy. """
        return self._overwrite_copy(src, _CORNER_SYMBOL, start)

    def with_node_string(self, src:OutputNode, start:int) -> __qualname__:
        """ Write the node's text starting at <start> and return a copy. """
        return self._overwrite_copy(src, src.text, start)

    def replace(self, *args) -> __qualname__:
        """ Override the basic string replace function to copy the node map as well. """
        other = _TextOutputLine(super().replace(*args))
        other._node_map = self._node_map
        return other

    def get_node_map(self) -> tuple:
        """ Return the tuple of node references, or an empty tuple if it's still None. """
        return self._node_map or ()


class _TextFormatter(object):
    """ Main parser/formatter for output text. On creation, builds a list of plaintext strings
        from a node tree and tracks additional info about node locations for tooltip support. """

    _output_lines: List[_TextOutputLine]  # Lines containing the raw text as well as each character's source node.

    def __init__(self, src:OutputNode):
        """ Create a list of special strings that will map to a text box with locational tooltip info. """
        self._output_lines = []
        if src.children:
            # Use the helper function to add lines recursively, starting at the left end with no placeholders.
            self._draw_node(src, 0, _TextOutputLine())
            self._output_lines.reverse()
        else:
            # An empty output means we didn't find any complete matches when we parsed it.
            word_len = len(src.text)
            self._output_lines = [_TextOutputLine().with_node_string(src, 0),
                                  _TextOutputLine(_LINE_SYMBOL * word_len),
                                  _TextOutputLine("?" * word_len)]

    def _draw_node(self, src:OutputNode, offset:int, placeholders:_TextOutputLine) -> None:
        """ Add lines of vertical cascaded plaintext to the string list. They are added recursively in reverse order.
            This means that the order must be reversed back by the caller at the top level. """
        text = src.text
        children = src.children
        out = self._output_lines
        # If there are children, start adding results in reverse order building up.
        if children:
            top = placeholders
            for child in reversed(children):
                if child.is_separator:
                    # If it's a separator, add slashes behind the previous line and do nothing else.
                    out.append(out.pop().replace(' ', '/'))
                else:
                    start = child.attach_start
                    wp = start + offset
                    # Add child recursively.
                    self._draw_node(child, wp, placeholders)
                    # Add a line with the bottom connector.
                    # If the text leads with a hyphen, the connector shouldn't cover it.
                    bottom_len = len(child.text)
                    if not child.children and wp > 0 and child.text[0] == KEY_SPLIT:
                        bottom_len -= 1
                    out.append(placeholders.with_container(child, wp, bottom_len, "INV" if child.is_inversion else "BOTTOM"))
                    # Place this child's top connector on the holding container.
                    top = top.with_container(child, wp, child.attach_length, "TOP")
                    # Add a permanent connector line to the placeholders.
                    placeholders = placeholders.with_connector(child, wp)
            # Destroy the last line if the first child had one character (i.e. connection is a line).
            if out[-1][offset] in _LINE_CHARACTER_SET:
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

    def make_text(self) -> str:
        """ Make the final plaintext string by joining the list with newlines. Rule metadata is not included. """
        return "\n".join(self._output_lines)

    def make_node_info(self) -> Tuple[Sequence[Sequence[OutputNode]],Dict[OutputNode,List[tuple]]]:
        """ Compile and return the saved node info into a list grid and dict. """
        # Combine the rows and ranges from all lines into a dict by node.
        node_grid = [line.get_node_map() for line in self._output_lines]
        format_dict = defaultdict(list)
        for (row, nmap) in enumerate(node_grid):
            old_i = -1
            old_n = None
            for i, n in enumerate(nmap + (None,)):
                if n is not old_n:
                    if old_n is not None:
                        format_dict[old_n].append((row, old_i, i))
                    old_i, old_n = i, n
        return node_grid, format_dict


class CascadedTextDisplay(object):
    """ Cascaded plaintext representation of lexer output. One of the only top-level classes.
        Must be displayed with a monospaced font that supports Unicode box-drawing characters. """

    text: str                                    # Plaintext output.
    _node_grid: List[List[OutputNode]]           # List of lists of node references in [row][col] format.
    _format_dict: Dict[OutputNode, List[tuple]]  # Dict of special display info for each node.

    def __init__(self, src:OutputNode):
        """ Generate a text format map from a lexer-generated output tree. """
        # Compile the initial list from the node tree.
        output = _TextFormatter(src)
        # Generate and assign instance attributes.
        self.text = output.make_text()
        self._node_grid, self._format_dict = output.make_node_info()

    def get_info_at(self, x:int, y:int) -> Union[TextRuleInfo,None]:
        """ Find the character at (x/column, y/row) of the text format and see if it's part of a node display.
            If it is, make an info structure for that node and return it. If it isn't, return None. """
        if 0 <= y < len(self._node_grid):
            row = self._node_grid[y]
            if 0 <= x < len(row):
                node = row[x]
                if node is not None:
                    return self._make_format_info(node)

    def _make_format_info(self, node:OutputNode) -> TextRuleInfo:
        """ Make a format info structure for a given node, which consists of instructions to highlight
            and/or bold ranges of text (ordered left-to-right, top-to-bottom) with different colors. """
        row_formats = []
        info = TextRuleInfo(node.raw_keys, node.description, row_formats)
        nodes = []
        while node is not None:
            nodes.append(node)
            node = node.parent
        for level, n in enumerate(reversed(nodes)):
            rng_tuples = self._format_dict[n]
            last_row = rng_tuples[-1][0]
            for (row, start, end) in rng_tuples:
                # Color is based on the node depth and row position.
                # Only the last row of each node can be bold (box-drawing characters mess up).
                color = _text_color(level, row)
                row_formats.append(TextFormatInfo(row, start, end, color, row==last_row))
        return info


def _text_color(level:int, row:int) -> Tuple[int, int, int]:
    """ Return an RGB 0-255 color value for any possible text row position and node depth. """
    return min(192, level * 64), min(192, row * 8), 255
