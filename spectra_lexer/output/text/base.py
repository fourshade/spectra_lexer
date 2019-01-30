from spectra_lexer import pipe
from spectra_lexer.config import Configurable, CFGOption

from spectra_lexer.output.locator import NodeLocator
from spectra_lexer.output.node import OutputNode
from spectra_lexer.output.text.graph import CascadedTextGraph, CompressedTextGraph
from spectra_lexer.output.text.html import HTMLFormatter


class TextRenderer(Configurable):
    """ Base class for creating and formatting a monospaced text grid. """

    ROLE = "output_text"
    compressed: bool = CFGOption(False, "Compressed Display", "Compress the graph vertically to save space.")

    _formatter: HTMLFormatter = None  # Formats the output text based on which node is selected (if any).
    _locator: NodeLocator = None      # Finds which node the mouse is over during a mouseover event.

    @pipe("new_output_tree", "new_output_graph")
    def generate(self, tree:OutputNode) -> str:
        """ Generate text graph data (of either type) from a node tree. """
        graph_type = CompressedTextGraph if self.compressed else CascadedTextGraph
        # Render plaintext output lines and create node reference structures from the tree.
        lines, nodes = graph_type(tree).render()
        # Create a locator and formatter using these structures and keep them for later reference.
        self._formatter = HTMLFormatter(lines, nodes)
        self._locator = NodeLocator(nodes)
        # The graph is new, so format it in plaintext. It should should scroll to the top by default.
        return self._formatter.make_graph_text()

    @pipe("output_text_select", "new_output_selection")
    def select(self, row:int, col:int) -> OutputNode:
        """ Find the node owning the character at (row, col) of the text graph.
            Switch the arguments to put it in (x, y) order. If it belongs to a new node, return the reference. """
        if self._locator is not None:
            return self._locator.select_node_at(col, row)

    @pipe("new_output_selection", "new_output_graph", scroll_to=None)
    def format(self, node:OutputNode=None) -> str:
        """ Format and return the text graph with the selected node using HTML. Don't allow the graph to scroll. """
        return self._formatter.make_graph_text(node)
