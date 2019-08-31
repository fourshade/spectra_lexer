""" Base module for text graphing. Defines top-level graph classes and structures. """

from typing import Optional, Tuple

from .format import CompatFormatter, HTMLFormatter
from .layout import CascadedGraphLayout, CompressedGraphLayout
from .node import NodeFactory
from ..keys import KeyLayout
from ..rules import StenoRule


class StenoGraph:
    """ Formats and renders a monospaced text graph of a rule. """

    def __init__(self, index:NodeFactory, formatter:HTMLFormatter) -> None:
        self.index = index          # Contains mappings of nodes to rules and vice versa.
        self.formatter = formatter  # Formats the output text based on which node is selected (if any).

    def render(self, ref:str="", rule:StenoRule=None, select:bool=False) -> Tuple[str, Optional[StenoRule]]:
        """ Process and render a graph as HTML text with a section index and/or specific rule selected.
            Return the finished text and any valid rule selection. If <select> is True, highlight that selection. """
        node = selection = None
        if ref:
            node, selection = self.index.select_ref(ref)
        elif rule:
            node, selection = self.index.select_rule(rule)
        return self.formatter.to_html(node, select), selection


class GraphGenerator:
    """ Main graph generator class. Requires minimal external resources. """

    def __init__(self, layout:KeyLayout) -> None:
        self._sep = layout.SEP      # Steno key used as stroke separator.
        self._split = layout.SPLIT  # Steno key used to split sides in RTFCRE.

    def generate(self, rule:StenoRule, recursive:bool=True, compressed:bool=True, compat:bool=False) -> StenoGraph:
        """ Make a node tree out of the given rule, tracking the node<->rule relationships.
            Generate a text graph object from this tree using a layout and formatter defined by flags. """
        factory = NodeFactory(self._sep, self._split, recursive)
        root = factory.make_root(rule)
        layout = CompressedGraphLayout() if compressed else CascadedGraphLayout()
        graph = layout.build(root)
        formatter = CompatFormatter.from_graph(graph) if compat else HTMLFormatter.from_graph(graph)
        return StenoGraph(factory, formatter)
