from typing import List, Tuple

from spectra_lexer.output.text import generator
from spectra_lexer.output.text.html import HTMLFormatter
from spectra_lexer.output.node import OutputNode


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


class CascadedTextFormatter:
    """ Base class for creating and formatting a cascaded plaintext breakdown of steno translations.
        Output must be displayed with a monospaced font that supports Unicode box-drawing characters. """

    _formatter: HTMLFormatter = None  # Formats the output text based on which node is selected (if any).
    _locator: _NodeLocator = None     # Finds which node the mouse is over during a mouseover event.

    def generate(self, root:OutputNode) -> None:
        """ Generate a text graph for a node tree. """
        # Create plaintext output lines and node reference structures from the tree using the generator.
        lines, node_grid = generator.new_text_grid(root)
        # Create a locator and formatter using these structures and keep them for later reference.
        self._formatter = HTMLFormatter(lines, node_grid)
        self._locator = _NodeLocator(node_grid)

    def get_node_at(self, row:int, col:int) -> OutputNode:
        """ Find the character at (row, col) of the text graph. If it belongs to a new node, return the reference. """
        if self._locator is not None:
            return self._locator.get_node_at(row, col)

    def get_text_output(self, node:OutputNode=None) -> dict:
        """ Format and return the text graph with the selected node using HTML. Don't allow the graph to scroll.
            If <node> is None, the graph is new. In this case, plaintext is fine and it should scroll to the top.
            A full dict of parameters describing how to format the text should be provided as output. """
        d = {"text": self._formatter.make_graph_text(node)}
        if node is not None:
            d["scroll_to"] = None
        return d
