from typing import List, Optional, Tuple

from spectra_lexer import Component, pipe
from spectra_lexer.rules import StenoRule
from spectra_lexer.text.generator import generate_text_grid
from spectra_lexer.text.html import HTMLFormatter
from spectra_lexer.text.node import OutputNode, OutputTree


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


class CascadedTextFormatter(Component):
    """ Base class for creating and formatting a cascaded plaintext breakdown of steno translations.
        Output must be displayed with a monospaced font that supports Unicode box-drawing characters. """

    _formatter: HTMLFormatter = None  # Formats the output text based on which node is selected (if any).
    _locator: _NodeLocator = None     # Finds which node the mouse is over during a mouseover event.
    _last_node: OutputNode = None     # Most recent node from a locator event (for identity matching).

    @pipe("new_lexer_result", "new_output_graph")
    def make_graph(self, rule:StenoRule) -> str:
        """ Generate a display tree, text graph, and info for a steno rule and send it to the GUI. """
        root = OutputTree(rule)
        # Create plaintext output lines and node reference structures from the current tree using the generator.
        lines, node_grid = generate_text_grid(root)
        # Create a locator and formatter using these structures and keep them for later reference.
        self._formatter = HTMLFormatter(lines, node_grid)
        self._locator = _NodeLocator(node_grid)
        # Send the title and node data for the board diagram.
        self.engine_call("new_output_title", str(rule))
        self._send_board_info(root)
        # Send the new, unformatted text graph to the engine. It will re-scroll to the top by default.
        return self._formatter.make_graph_text()

    @pipe("output_format_node_at", "new_output_graph", scroll_to=None)
    def get_node_at(self, row:int, col:int) -> Optional[str]:
        """ Find the character at (row, col) of the text format and see if it's part of a node display.
            If it is, format it and display the board info and formatted text graph with that node selected.
            Make sure it doesn't affect the current scroll position. """
        if self._locator:
            node = self._locator.get_node_at(row, col)
            if node is None or node is self._last_node:
                return None
            # Store the current node so we can avoid repeated lookups.
            self._last_node = node
            # Send the node data and text separate so that board diagrams and text graphs can both update.
            self._send_board_info(node)
            return self._formatter.make_graph_text(node)

    def _send_board_info(self, node):
        """ Generate board diagram elements from steno keys and send them along with the description. """
        self.engine_call("new_output_info", node.raw_keys.for_display(), node.description)
