""" Base module for text graphing. Defines top-level graph classes and structures. """

from typing import Optional

from .formatter import HTMLFormatter
from .generator import CascadedTextGenerator, CompressedTextGenerator
from .locator import GridLocator
from .node import GraphNode
from spectra_lexer import Component
from spectra_lexer.steno.rules import StenoRule


class GraphRenderer(Component):
    """ Component class for creating and formatting a monospaced text graph from a rule. """

    recursive = Option("config", "graph:recursive_graph", True, "Include rules that make up other rules.")
    compressed = Option("config", "graph:compressed_display", True, "Compress the graph vertically to save space.")

    _last_node: GraphNode = None      # Most recent node from a select event (for identity matching).
    _locator: GridLocator = None      # Finds which node the mouse is over during a mouseover event.
    _formatter: HTMLFormatter = None  # Formats the output text based on which node is selected (if any).

    @pipe("new_lexer_result", "new_interactive_text", html=True, mouse=True)
    def generate(self, rule:StenoRule) -> str:
        """ Generate text graph data (of either type) from a rule based on config settings. """
        # Send the rule string as a status message (this doubles as the title in the GUI).
        self.engine_call("new_status", str(rule))
        # Make a node tree layout out of the given rule.
        root = GraphNode.for_display(rule, self.recursive)
        # Generate and render all text objects into standard strings and node grids indexed by position.
        generator_type = CompressedTextGenerator if self.compressed else CascadedTextGenerator
        lines, nodes = generator_type(root).render()
        # Create a locator and formatter using these structures and keep them for later reference.
        self._locator = GridLocator(nodes)
        self._formatter = HTMLFormatter(lines, nodes)
        # The graph is new, so render it with no highlighting or boldface. It should scroll to the top by default.
        return self._formatter.make_graph_text()

    @pipe("text_mouse_action", "new_graph_selection")
    def select(self, row:int, col:int, clicked:bool=False) -> Optional[StenoRule]:
        """ Find the node owning the element at (row, col) of the graph. If that node is new, send out its rule. """
        if self._locator is None:
            return None
        node = self._locator.select(row, col)
        if node is None or node is self._last_node:
            return None
        # Store the new object reference so we can avoid repeated lookups.
        self._last_node = node
        # Also render and send the graph with this node highlighted. Don't allow the graph to scroll.
        text = self._formatter.make_graph_text(node)
        self.engine_call("new_interactive_text", text, html=True, mouse=True, scroll_to=None)
        return node.rule
