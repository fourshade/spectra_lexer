from typing import List, Optional, Tuple

from spectra_lexer import pipe
from spectra_lexer.config import Configurable, CFGOption
from spectra_lexer.output import board
from spectra_lexer.output.node import OutputNode, OutputTree
from spectra_lexer.output.text import TextGenerator

from spectra_lexer.rules import StenoRule


class DisplayEngine(Configurable):
    """ Main component of the display package. Contains the board diagram generator and the text graph generator. """

    ROLE = "output"
    compressed: bool = CFGOption(False, "Compressed Display", "Compress the graph vertically to save space.")

    _grapher: TextGenerator = None  # Stores and calculates all information related to text graphing.

    @pipe("new_lexer_result", "new_output_node", is_new=True)
    def make_tree(self, rule:StenoRule) -> OutputTree:
        """ Generate a display tree for a steno rule and send the title. """
        tree = OutputTree(rule)
        self.engine_call("new_output_title", str(rule))
        # Make a new text graph generator.
        self._grapher = TextGenerator(tree, compressed=self.compressed)
        return tree

    @pipe("output_select_node_at", "new_output_node", is_new=False)
    def select_node_at(self, y:int, x:int) -> Optional[OutputNode]:
        """ Find the node at position (y, x) of the current graph. For text, this is (row, col) in characters.
            If a node occupies this position, get the reference and send a node select command. """
        if self._grapher is None:
            return None
        return self._grapher.get_node_at(y, x)

    @pipe("new_output_node", "new_output_graph", unpack=True)
    def make_graph(self, node:OutputNode, is_new:bool) -> dict:
        """ Format and display the text graph with the selected node (or None if it's a new graph). """
        return self._grapher.graph(node if not is_new else None)

    @pipe("new_output_node", "new_output_board", unpack=True)
    def make_board(self, node:OutputNode, is_new:bool) -> Tuple[List[List[str]], str]:
        """ Generate and display board diagram elements for a specific node in the graph. """
        return board.make_board_info(node)
