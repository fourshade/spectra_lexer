from collections import defaultdict

from typing import Dict, List, Tuple

from spectra_lexer.display import OutputDisplay
from spectra_lexer.display.base import OutputNode
from spectra_lexer.keys import KEY_SPLIT
from spectra_lexer.rules import StenoRule

# Symbols used to represent text "containers" in the graph. The middle of each one is replicated to fill gaps.
_CONTAINER_SYMBOLS = {"TOP":    "├─┘",
                      "BOTTOM": "├─┐",
                      "S_BEND": "└─┐",
                      "Z_BEND": "┌─┘",
                      "INV":    "◄═►"}
# Symbols connecting containers together.
_LINE_SYMBOL = "│"
_CORNER_SYMBOL = "┐"
# RGB 0-255 colors of the root node and starting color of other nodes when highlighted.
_ROOT_COLOR = (255, 64, 64)
_BASE_COLOR = (0, 0, 255)


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

    def _overwrite_copy(self, s:str, src:OutputNode, start:int) -> __qualname__:
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

    def with_container(self, src:OutputNode, start:int, length:int, position:str) -> __qualname__:
        """ Write a "container" ├--┐ at index <start> and return a copy. """
        return self._overwrite_copy(_text_container(length, position), src, start)

    def with_connector(self, src:OutputNode, start:int) -> __qualname__:
        """ Write a vertical line connector at index <start> and return a copy. """
        return self._overwrite_copy(_LINE_SYMBOL, src, start)

    def with_corner(self, src:OutputNode, start:int) -> __qualname__:
        """ Write a corner character at index <start> and return a copy. """
        return self._overwrite_copy(_CORNER_SYMBOL, src, start)

    def with_node_string(self, src:OutputNode, start:int) -> __qualname__:
        """ Write the node's text starting at <start> and return a copy. """
        return self._overwrite_copy(src.text, src, start)

    def replace(self, *args) -> __qualname__:
        """ Override the basic string replace function to copy the node map as well. """
        other = _TextOutputLine(super().replace(*args))
        other._node_map = self._node_map
        return other

    def get_node_map(self) -> tuple:
        """ Return the tuple of node references, or an empty tuple if it's still None. """
        return self._node_map or ()


class _TextGenerator:
    """ Main generator for output text. On creation, builds a list of plaintext strings
        from a node tree and tracks additional info about node locations for tooltip support. """

    _output_lines: List[_TextOutputLine]  # Lines containing the raw text as well as each character's source node.

    def __init__(self, src:OutputNode):
        """ Create a list of special strings that will map to a text box with locational info. """
        if src.children:
            # Use the helper function to add lines recursively, starting at the left end with no placeholders.
            output_lines = []
            self._draw_node(output_lines, src, 0, _TextOutputLine())
            output_lines.reverse()
        else:
            # An empty output means we didn't find any complete matches when we parsed it.
            output_lines = self._incomplete_graph(src)
        self._output_lines = output_lines

    def _draw_node(self, out:List[_TextOutputLine], src:OutputNode, offset:int, placeholders:_TextOutputLine) -> None:
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
                    out.append(out.pop().replace(' ', '/'))
                else:
                    start = child.attach_start
                    wp = start + offset
                    # Add child recursively.
                    self._draw_node(out, child, wp, placeholders)
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

    @staticmethod
    def _incomplete_graph(src:OutputNode) -> List[_TextOutputLine]:
        """ Draw a graph with the base node along with lines that show the lexer's failure to make a good guess. """
        word_len = len(src.text)
        return [_TextOutputLine().with_node_string(src, 0),
                _TextOutputLine(_LINE_SYMBOL * word_len),
                _TextOutputLine("?" * word_len)]

    def get_text_lines(self) -> List[str]:
        """ Return the generated strings, free of the context of any metadata they carry as a subclass. """
        return self._output_lines

    def get_node_info(self) -> Tuple[List[Tuple[OutputNode]], Dict[OutputNode, List[Tuple[int,int,int]]]]:
        """ Compile all saved node info into a 2D grid (indexed by position) and dict (indexed by node). """
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


def _text_color(level:int, row:int) -> Tuple[int,int,int]:
    """ Return an RGB 0-255 color value for any possible text row position and node depth. """
    if level == 0 and row == 0:
        return _ROOT_COLOR
    r, g, b = _BASE_COLOR
    r += min(192, level * 64)
    g += min(192, row * 8)
    return r, g, b


def _format_row(lines:List[str], idx:int, start:int, end:int, color:Tuple[int,int,int], bold:bool) -> None:
    """ Format a section of a row in a list of strings with HTML color and/or boldface. """
    if start < end:
        line = lines[idx]
        text = line[start:end]
        text = """<span style="color:#{0:02x}{1:02x}{2:02x};">{3}</span>""".format(*color, text)
        if bold:
            text = "<b>{}</b>".format(text)
        lines[idx] = "".join((line[:start], text, line[end:]))


class _TextFormatter:
    """ Receives a list of text lines and instructions on formatting to apply in various places when any given
        node is highlighted. Creates structures with explicit formatting operations to be used by the GUI. """

    _lines: List[str]                                         # Lines containing the raw text.
    _format_dict: Dict[OutputNode, List[Tuple[int,int,int]]]  # Dict of special display info for each node.

    def __init__(self, lines:List[str], format_dict:Dict[OutputNode, List[Tuple[int,int,int]]]):
        self._lines = lines
        self._format_dict = format_dict

    def make_graph_text(self, lines:List[str]=None) -> str:
        """ Make a full graph text string by joining a list of line strings and setting the preformatted tag.
            If no lines are specified, use the last set of raw text strings unformatted. """
        if lines is None:
            lines = self._lines
        return "<pre>"+"\n".join(lines)+"</pre>"

    def make_formatted_text(self, node:OutputNode) -> str:
        """ Make a formatted text graph string for a given node, with highlighted and/or bolded ranges of text. """
        lines = self._lines[:]
        # Color the full ancestry line of the selected node, starting with that node and going up.
        # This ensures that formatting happens right-to-left on rows with more than one operation.
        nodes = node.get_ancestors()
        derived_start = sum(n.attach_start for n in nodes)
        derived_end = derived_start + node.attach_length
        level = len(nodes) - 1
        for n in nodes:
            rng_tuples = self._format_dict[n]
            # All of the node's characters above the text will be box-drawing characters.
            # These mess up when bolded, so only bold the last row (first in the reversed iterator).
            bold = True
            for (row, start, end) in reversed(rng_tuples):
                # If this is the last row of any ancestor node, only highlight the text our node derives from.
                if bold and n is not node:
                    start, end = derived_start, derived_end
                _format_row(lines, row, start, end, _text_color(level, row), bold)
                bold = False
            level -= 1
        return self.make_graph_text(lines)


class _NodeLocator:
    """ Simple implementation of an indexer with bounds checking for a list of lists with non-uniform lengths. """

    _node_grid: List[Tuple[OutputNode]]  # List of tuples of node references in [row][col] format.

    def __init__(self, node_grid:List[Tuple[OutputNode]]):
        self._node_grid = node_grid

    def get_node_at(self, row:int, col:int) -> OutputNode:
        """ Return the node that was responsible for the text character at (row, col).
            Return None if no node owns that character or the index is out of range. """
        if 0 <= row < len(self._node_grid):
            node_row = self._node_grid[row]
            if 0 <= col < len(node_row):
                return node_row[col]


class CascadedTextDisplay(OutputDisplay):
    """ Generates cascaded plaintext representation of lexer output. One of the only top-level classes.
        Output must be displayed with a monospaced font that supports Unicode box-drawing characters. """

    _formatter: _TextFormatter = None   # Formats the output text based on which node is selected (if any).'
    _locator: _NodeLocator = None       # Finds which node the mouse is over during a mouseover event.
    _last_node: OutputNode = None       # Most recent node from a mouse move event.

    def engine_commands(self) -> dict:
        """ Individual components must define the signals they respond to and the appropriate callbacks. """
        return {**super().engine_commands(),
                "new_window":      self.on_new_window,
                "display_rule":    self.show_graph,
                "display_info_at": self.show_info_at,}

    def on_new_window(self) -> None:
        """ Clear the last locator so that the old output isn't drawn on a fresh window. """
        self._locator = None

    def show_graph(self, rule:StenoRule) -> None:
        """ Generate a text graph and info for a steno rule and send it to the GUI. """
        # Start by making a generic rule node tree. The entire tree is contained by the root node.
        root_node = self.make_tree(rule)
        # Compile the plaintext output and node reference structures from the tree using the generator.
        generator = _TextGenerator(root_node)
        lines = generator.get_text_lines()
        node_grid, format_dict = generator.get_node_info()
        # Create a locator and formatter using these structures.
        self._formatter = _TextFormatter(lines, format_dict)
        self._locator = _NodeLocator(node_grid)
        # Send the title, unformatted text graph, and root node info to the GUI.
        self.engine_call("gui_display_title", str(rule))
        self.engine_call("gui_display_graph", self._formatter.make_graph_text())
        self.engine_call("gui_display_info", root_node.raw_keys, root_node.description)

    def show_info_at(self, row:int, col:int) -> None:
        """ Find the character at (row, col) of the text format and see if it's part of a node display.
            If it is (and isn't the one currently shown), make an info structure for that node and display it. """
        if self._locator:
            node = self._locator.get_node_at(row, col)
            if node is not None and node is not self._last_node:
                # Send the new formatted text to the GUI. Make sure it doesn't affect the current scroll position.
                self.engine_call("gui_display_graph", self._formatter.make_formatted_text(node), False)
                # Send parts from the given rule info to the GUI.
                self.engine_call("gui_display_info", node.raw_keys, node.description)
            # Store the current node so we can avoid redraw.
            self._last_node = node
