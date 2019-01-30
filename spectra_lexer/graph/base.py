from typing import Optional

from spectra_lexer import pipe
from spectra_lexer.config import Configurable, CFGOption
from spectra_lexer.graph.node import GraphNode
from spectra_lexer.graph.text import TextGraph
from spectra_lexer.rules import StenoRule


class GraphRenderer(Configurable):
    """ Main component class for creating and formatting a monospaced text graph.
        The graph object itself does most of the work; this one just exists to pass messages. """

    ROLE = "graph"
    recursive: bool = CFGOption(False,  "Recursive Graph",    "Include rules that make up other rules.")
    compressed: bool = CFGOption(False, "Compressed Display", "Compress the graph vertically to save space.")

    _graph: TextGraph = None      # Generates text graphs and processes selections.
    _last_node: GraphNode = None  # Most recent node from a select event (for identity matching).

    @pipe("new_lexer_result", "new_graph_text")
    def generate(self, rule:StenoRule) -> str:
        """ Generate text graph data (of either type) from a rule. """
        # Send the rule string as a status message (this doubles as the title in the GUI).
        self.engine_call("new_status", str(rule))
        # Create the graph object based on config settings.
        self._graph = TextGraph(rule, recursive=self.recursive, compressed=self.compressed)
        # The graph is new, so render it without no node selected. It should should scroll to the top by default.
        return self._graph.render()

    @pipe("graph_select", "new_graph_selection")
    def select(self, x:int, y:int, clicked:bool=False) -> Optional[StenoRule]:
        """ Find the node owning the element at (x, y) of the graph. If it belongs to a new node, send out its rule. """
        if self._graph is None:
            return None
        node = self._graph.select_node(x, y)
        if node is None or node is self._last_node:
            return None
        # Store the new object reference so we can avoid repeated lookups.
        self._last_node = node
        # Also render and send the graph with the selected node. Don't allow the graph to scroll.
        text = self._graph.render(node)
        self.engine_call("new_graph_text", text, scroll_to=None)
        return node.rule
