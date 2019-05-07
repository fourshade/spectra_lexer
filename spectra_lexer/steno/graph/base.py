""" Base module for text graphing. Defines top-level graph classes and structures. """

from .generator import CascadedTextGenerator, CompressedTextGenerator
from .html import HTMLFormatter
from .locator import GridLocator
from .node import GraphNode, NodeOrganizer
from .text import SectionedTextField
from ..rules import StenoRule
from spectra_lexer.core import Component


class GraphRenderer(Component):
    """ Component class for creating and formatting a monospaced text graph from a rule. """

    recursive = resource("config:graph:recursive_graph", True, desc="Include rules that make up other rules.")
    compressed = resource("config:graph:compressed_display", True, desc="Compress the graph vertically to save space.")
    layout = resource("system:layout")

    _organizer: NodeOrganizer = None        # Makes node tree layouts out of rules.
    _formatter: HTMLFormatter = None        # Formats the output text based on which node is selected (if any).
    _locator: GridLocator = None            # Finds which node the mouse is over during a mouseover event.
    _last_node: GraphNode = None            # Most recent node from a select event (for identity matching).

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
        # Create  a text field, formatter, and locator using these structures and keep them for later reference.
        text_field = SectionedTextField(lines, nodes)
        self._formatter = HTMLFormatter(text_field)
        self._locator = GridLocator(nodes)
        self._display_selection(root, new=True)

    @on("text_mouse_action")
    def select_character(self, row:int, col:int, clicked:bool=False) -> None:
        """ Find the node owning the character at (row, col) of the graph. If that node is new, send out its rule. """
        if self._locator is None:
            return
        node = self._locator.get(row, col)
        if node is None or node is self._last_node:
            return
        # Store the node reference so we can avoid repeated lookups on small mouse deltas.
        self._last_node = node
        self._display_selection(node)

    @on("graph_select_rule")
    def select_rule(self, rule:StenoRule) -> None:
        """ Find the first node created from <rule>, if any, and select it. """
        if self._locator is None:
            return
        node = self._organizer.node_from(rule)
        if node is not None:
            self._display_selection(node)

    def _display_selection(self, node:GraphNode, new:bool=False) -> None:
        """ Render and send the graph with a node highlighted. If None, render with no highlighting or boldface. """
        self._formatter.start()
        if not new:
            self._formatter.highlight(node)
        text = self._formatter.finish()
        # A new graph should scroll to the top by default. Otherwise don't allow the graph to scroll.
        self.engine_call("new_graph_text", text, scroll_to="top" if new else None)
        # Get the rule originally associated with this node and send it to the board.
        self.engine_call("board_display_rule", self._organizer.rule_from(node))
