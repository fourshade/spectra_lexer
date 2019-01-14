from typing import List, Tuple, Optional

from spectra_lexer import Component, pipe
from spectra_lexer.output import board
from spectra_lexer.output.node import OutputNode, OutputTree
from spectra_lexer.output.text import CascadedTextFormatter

from spectra_lexer.rules import StenoRule


class DisplayEngine(Component):
    """ Main component of the display package. Contains the board diagram generator and the text graph generator. """

    ROLE = "output"

    _graph: CascadedTextFormatter  # Stores and calculates all information related to text graphing.
    _last_node: OutputNode = None  # Most recent node from a select event (for identity matching).

    def __init__(self):
        self._graph = CascadedTextFormatter()

    @pipe("new_lexer_result", "new_output_node", is_new=True)
    def make_tree(self, rule:StenoRule) -> OutputNode:
        """ Generate a display tree for a steno rule and send the title. """
        root = OutputTree(rule)
        self.engine_call("new_output_title", str(rule))
        # Make a new, unformatted text graph to send to the engine. It will re-scroll to the top by default.
        self._graph.generate(root)
        return root

    @pipe("output_select_node_at", "new_output_node", is_new=False)
    def select_node_at(self, y:int, x:int) -> Optional[OutputNode]:
        """ Find the node at position (y, x) of the graph. For text, this is (row, col) in characters.
            If a node occupies this position, get the reference and send a node select command. """
        node = self._graph.get_node_at(y, x)
        if node is None or node is self._last_node:
            return None
        # Store the current node so we can avoid repeated lookups.
        self._last_node = node
        # Format and display the text graph, but make sure it doesn't affect the current scroll position.
        return node

    @pipe("new_output_node", "new_output_graph", unpack=dict)
    def make_graph(self, node:OutputNode, is_new:bool) -> dict:
        """ Format and display the text graph with the selected node (or None if it's a new graph). """
        return self._graph.get_text_output(node if not is_new else None)

    @pipe("new_output_node", "new_output_board", unpack=True)
    def make_board_info(self, node:OutputNode, is_new:bool) -> Tuple[List[List[str]], str]:
        """ Generate and display board diagram elements for a specific node in the graph. """
        return board.make_board_info(node)
