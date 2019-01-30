from typing import List, Optional

from spectra_lexer.output.text.cascaded import CascadedTextGraph
from spectra_lexer.output.text.compressed import CompressedTextGraph
from spectra_lexer.output.text.html import HTMLFormatter
from spectra_lexer.output.node import OutputNode, OutputTree


class _TextNodeLocator:
    """ Simple implementation of an indexer with bounds checking for a list of lists with non-uniform lengths.
        Works well for text graphs (which have a relatively small number of rows and columns compared to pixels). """

    _node_grid: List[List[OutputNode]]  # List of tuples of node references in [row][col] format.

    def __init__(self, node_grid:List[List[OutputNode]]):
        self._node_grid = node_grid

    def get_node_at(self, row:int, col:int) -> OutputNode:
        """ Return the node that was responsible for the text character at (row, col).
            Return None if no node owns that character or the index is out of range. """
        if 0 <= row < len(self._node_grid):
            node_row = self._node_grid[row]
            if 0 <= col < len(node_row):
                return node_row[col]


class TextGenerator:
    """ Base class for creating and formatting a monospaced text grid. """

    _formatter: HTMLFormatter      # Formats the output text based on which node is selected (if any).
    _locator: _TextNodeLocator     # Finds which node the mouse is over during a mouseover event.
    _last_node: OutputNode = None  # Most recent node from a select event (for identity matching).

    def __init__(self, tree:OutputTree, compressed=False):
        """ Generate text graph data (of either type) from a node tree. """
        graph_type = CompressedTextGraph if compressed else CascadedTextGraph
        # Create plaintext output lines and node reference structures from the tree.
        graph = graph_type(tree)
        lines, nodes = graph.compile_data()
        # Create a locator and formatter using these structures and keep them for later reference.
        self._formatter = HTMLFormatter(lines, nodes)
        self._locator = _TextNodeLocator(nodes)

    def get_node_at(self, row:int, col:int) -> Optional[OutputNode]:
        """ Find the character at (row, col) of the text graph. If it belongs to a new node, return the reference. """
        node = self._locator.get_node_at(row, col)
        if node is None or node is self._last_node:
            return None
        # Store the current node so we can avoid repeated lookups.
        self._last_node = node
        return node

    def graph(self, node:OutputNode=None) -> dict:
        """ Format and return the text graph with the selected node using HTML. Don't allow the graph to scroll.
            If <node> is None, the graph is new. In this case, plaintext is fine and it should scroll to the top.
            A full dict of parameters describing how to format the text should be provided as output. """
        d = {"text": self._formatter.make_graph_text(node)}
        if node is not None:
            d["scroll_to"] = None
        return d
