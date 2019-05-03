""" Base module for text graphing. Defines top-level graph classes and structures. """

from .formatter import HTMLFormatter
from .generator import CascadedTextGenerator, CompressedTextGenerator
from .locator import GridLocator
from .node import GraphNode, NodeOrganizer
from spectra_lexer.core import Component
from spectra_lexer.steno.rules import StenoRule


class GraphRenderer(Component):
    """ Component class for creating and formatting a monospaced text graph from a rule. """

    recursive = resource("config:graph:recursive_graph", True, desc="Include rules that make up other rules.")
    compressed = resource("config:graph:compressed_display", True, desc="Compress the graph vertically to save space.")
    layout = resource("system:layout")

    _organizer: NodeOrganizer = None  # Makes node tree layouts out of rules.
    _locator: GridLocator = None      # Finds which node the mouse is over during a mouseover event.
    _formatter: HTMLFormatter = None  # Formats the output text based on which node is selected (if any).
    _last_node: GraphNode = None      # Most recent node from a select event (for identity matching).

    @on("new_output")
    def generate(self, rule:StenoRule) -> None:
        """ Generate text graph data (of either type) from an output rule based on config settings. """
        if self._organizer is None:
            self._organizer = NodeOrganizer(self.layout.SEP, self.layout.SPLIT)
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
        self._display_selection(root, new=True)

    @on("text_mouse_action")
    def select_character(self, row:int, col:int, clicked:bool=False) -> None:
        """ Find the node owning the character at (row, col) of the graph. If that node is new, send out its rule. """
        if self._locator is None:
            return
        node = self._locator.select(row, col)
        if node is None or node is self._last_node:
            return
        # Store the node reference so we can avoid repeated lookups on small mouse deltas.
        self._last_node = node
        self._display_selection(node)

    @on("graph_select_rule")
    def select_rule(self, rule:StenoRule) -> None:
        """ Find the first node created from <rule>, if any, and select it. """
        if self._formatter is None:
            return
        # The formatter is a dict of nodes; just run a quick search through its keys.
        for node in self._formatter:
            if node.rule is rule:
                self._display_selection(node)

    def _display_selection(self, node:GraphNode, new:bool=False) -> None:
        """ Render and send the graph with a node highlighted. If None, render with no highlighting or boldface. """
        text = self._formatter.make_graph_text(node if not new else None)
        # A new graph should scroll to the top by default. Otherwise don't allow the graph to scroll.
        self.engine_call("new_graph_text", text, scroll_to="top" if new else None)
        self.engine_call("board_display_rule", node.rule)
