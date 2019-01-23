""" Base module for text graphing. Defines top-level graph classes and structures. """

from spectra_lexer.graph.text.formatter import HTMLFormatter
from spectra_lexer.graph.text.locator import GridLocator
from spectra_lexer.graph.text.node import TextNode
from spectra_lexer.graph.text.layout import CompressedTextLayout, CascadedTextLayout
from spectra_lexer.rules import StenoRule


class TextGraph:
    """ A complete text graph created from a rule. """

    _locator: GridLocator = None      # Finds which node the mouse is over during a mouseover event.
    _formatter: HTMLFormatter = None  # Formats the output text based on which node is selected (if any).

    def __init__(self, rule:StenoRule, compressed=False):
        """ Make a node tree layout out of the given rule to display. """
        layout_type = CompressedTextLayout if compressed else CascadedTextLayout
        # Render all text objects into standard strings and node grids indexed by position.
        lines, nodes = layout_type.for_display(rule).render()
        # Create a locator and formatter using these structures and keep them for later reference.
        self._locator = GridLocator(nodes)
        range_dict = self._locator.range_dict()
        self._formatter = HTMLFormatter(lines, range_dict)

    def select_node(self, col:int, row:int) -> TextNode:
        """ Return the node reference (if any) at position (row, col) of the graph. """
        return self._locator.select(row, col)

    def render(self, node:TextNode=None) -> str:
        """ Format the selected node using HTML. If node is None, don't apply any highlighting or boldface. """
        return self._formatter.make_graph_text(node)