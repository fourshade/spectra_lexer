""" Base module for text graphing. Defines top-level graph classes and structures. """

from typing import Optional

from .formatter import HTMLFormatter
from .generator import CascadedTextGenerator, CompressedTextGenerator
from .locator import GridLocator
from .node import GraphNode, NodeOrganizer
from spectra_lexer import Component
from spectra_lexer.steno.rules import StenoRule
from spectra_lexer.steno.system import StenoSystem


class GraphRenderer(Component):
    """ Component class for creating and formatting a monospaced text graph from a rule. """

    recursive = resource("config:graph:recursive_graph", True, desc="Include rules that make up other rules.")
    compressed = resource("config:graph:compressed_display", True, desc="Compress the graph vertically to save space.")

    _organizer: NodeOrganizer = None  # Makes node tree layouts out of rules.
    _locator: GridLocator = None      # Finds which node the mouse is over during a mouseover event.
    _formatter: HTMLFormatter = None  # Formats the output text based on which node is selected (if any).
    _last_node: GraphNode = None      # Most recent node from a select event (for identity matching).

    @resource("system")
    def set_system(self, system:StenoSystem) -> None:
        """ Make a node organizer that can parse the current key set. """
        self._organizer = NodeOrganizer(system.layout.SEP, system.layout.SPLIT)

    @on("new_output", pipe_to="new_graph_text")
    def generate(self, rule:StenoRule) -> Optional[str]:
        """ Generate text graph data (of either type) from an output rule based on config settings. """
        if self._organizer is None:
            return None
        # Send the rule string to the GUI as a title message.
        self.engine_call("new_title_text", str(rule))
        # Make a node tree layout out of the given rule.
        root = self._organizer.make_tree(rule, self.recursive)
        # Generate and render all text objects into standard strings and node grids indexed by position.
        generator_type = CompressedTextGenerator if self.compressed else CascadedTextGenerator
        lines, nodes = generator_type(root).render()
        # Create a locator and formatter using these structures and keep them for later reference.
        self._locator = GridLocator(nodes)
        self._formatter = HTMLFormatter(lines, nodes)
        # The graph is new, so render it with no highlighting or boldface. It should scroll to the top by default.
        return self._formatter.make_graph_text()

    @on("text_mouse_action", pipe_to="new_graph_selection")
    def select_character(self, row:int, col:int, clicked:bool=False) -> Optional[StenoRule]:
        """ Find the node owning the character at (row, col) of the graph. If that node is new, send out its rule. """
        if self._locator is None:
            return None
        node = self._locator.select(row, col)
        if node is None or node is self._last_node:
            return None
        return self._display_selection(node)

    @on("text_display_rule", pipe_to="new_graph_selection")
    def display_rule(self, rule:StenoRule) -> Optional[StenoRule]:
        """ Find the first node created from <rule>, if any, and select it. """
        if self._formatter is None:
            return None
        # The formatter is a dict of nodes; just run a quick search through its keys.
        for node in self._formatter:
            if node.rule is rule:
                return self._display_selection(node)

    def _display_selection(self, node:GraphNode) -> StenoRule:
        """ Render and send the graph with <node> highlighted. Don't allow the graph to scroll. """
        text = self._formatter.make_graph_text(node)
        self.engine_call("new_graph_text", text, scroll_to=None)
        # Store the object reference so we can avoid repeated lookups and send the rule to the board diagram.
        self._last_node = node
        return node.rule
