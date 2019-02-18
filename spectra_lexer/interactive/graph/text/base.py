""" Base module for text graphing. Defines top-level graph classes and structures. """

from spectra_lexer.interactive.graph.text.formatter import HTMLFormatter
from spectra_lexer.interactive.graph.text.generator import CascadedTextGenerator, CompressedTextGenerator
from spectra_lexer.interactive.graph.text.locator import GridLocator
from spectra_lexer.interactive.graph.text.node import TextNode
from spectra_lexer.rules import StenoRule


class TextGraph:
    """ A complete text graph created from a rule. """

    _locator: GridLocator = None      # Finds which node the mouse is over during a mouseover event.
    _formatter: HTMLFormatter = None  # Formats the output text based on which node is selected (if any).

    def __init__(self, rule:StenoRule, recursive:bool=False, compressed:bool=False):
        """ Make a node tree layout out of the given rule to display. """
        root = TextNode.for_display(rule, recursive)
        # Generate and render all text objects into standard strings and node grids indexed by position.
        generator_type = CompressedTextGenerator if compressed else CascadedTextGenerator
        lines, nodes = generator_type(root).render()
        # Create a locator and formatter using these structures and keep them for later reference.
        self._locator = GridLocator(nodes)
        self._formatter = HTMLFormatter(lines, nodes)

    def select_node(self, col:int, row:int) -> TextNode:
        """ Return the node reference (if any) at position (row, col) of the graph. """
        return self._locator.select(row, col)

    def render(self, node:TextNode=None) -> str:
        """ Format the selected node using HTML. If node is None, don't apply any highlighting or boldface. """
        return self._formatter.make_graph_text(node)
