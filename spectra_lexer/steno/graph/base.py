""" Base module for text graphing. Defines top-level graph classes and structures. """

from typing import Iterable, List, Optional

from .html import HTMLTextField
from .layout import CascadedGraphLayout, CompressedGraphLayout
from .node import GraphNode, NodeFactory
from spectra_lexer.resource import StenoRule


class StenoGraph:
    """ Class for a formatted monospaced text graph of a rule. Layouts arrange the children however they want. """

    _factory: NodeFactory             # Creates nodes and contains mappings of each one to its rule.
    _ref_grid: List[List[GraphNode]]  # List of lists of node references in [row][col] format.
    _formatter: HTMLTextField         # Formats the output text based on which node is selected (if any).

    def __init__(self, rule:StenoRule, sep:str, split:str, recursive:bool=True, compressed:bool=True):
        """ Make a node tree layout out of the given rule and parameters.
            Lay out and render all text objects into character lines and node reference lists. """
        self._factory = NodeFactory(sep, split, recursive)
        root = self._factory(rule)
        layout_cls = CompressedGraphLayout if compressed else CascadedGraphLayout
        lines, nodes = layout_cls(root).render()
        self._ref_grid = nodes
        self._formatter = HTMLTextField(lines, nodes)

    def process(self, *, ref:str="", rule:StenoRule=None, select:bool=False) -> tuple:
        """ Process and render a graph with a section index and/or rule selected.
            If <select> is True, highlight these as well. Return the finished text and any valid rule selection. """
        if rule is None:
            node = self._formatter.node_at(ref)
        else:
            node = self._factory.rule_to_node(rule)
        return self._formatter.to_html(node, intense=select), self._factory.node_to_rule(node)


def _filtermap(fn, iterable) -> list:
    return [*filter(None, map(fn, iterable))]
