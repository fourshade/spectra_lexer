""" Base module for text graphing. Defines top-level graph classes and structures. """

from functools import lru_cache
from typing import Dict, List, Optional, Tuple

from .html import HTMLTextField
from .layout import CascadedGraphLayout, CompressedGraphLayout
from .node import GraphNode, NodeFactory
from ..base import LX
from spectra_lexer.resource import StenoRule


class StenoGraph(NodeFactory):
    """ Class for a formatted monospaced text graph of a rule. Layouts arrange the children however they want. """

    _rules_by_node: Dict[StenoRule, GraphNode]  # Mapping of each rule to its generated node.
    _nodes_by_rule: Dict[GraphNode, StenoRule]  # Mapping of each generated node to its rule.
    _ref_grid: List[List[GraphNode]]  # List of lists of node references in [row][col] format.
    _formatter: HTMLTextField         # Formats the output text based on which node is selected (if any).

    def __init__(self, rule:StenoRule, sep:str, split:str, recursive:bool=True, compressed:bool=True):
        """ Make a node tree layout out of the given rule and parameters, tracking the node<->rule relationships.
            Lay out and render all text objects into character lines and node reference lists. """
        super().__init__(sep, split, recursive)
        self._rules_by_node = {}
        self._nodes_by_rule = {}
        root = self.make_tree(rule)
        layout_cls = CompressedGraphLayout if compressed else CascadedGraphLayout
        lines, nodes = layout_cls(root).render()
        self._ref_grid = nodes
        self._formatter = HTMLTextField(lines, nodes)

    def _make_node(self, rule:StenoRule, *args) -> GraphNode:
        """ Keep track of the node and its rule in case we need one from the other. """
        node = super()._make_node(rule, *args)
        self._rules_by_node[rule] = node
        self._nodes_by_rule[node] = rule
        return node

    def render(self, index:str="", rule:StenoRule=None, select:bool=False) -> Tuple[str, Optional[StenoRule]]:
        """ Process and render a graph as HTML text with a section index and/or specific rule selected.
            Return the finished text and any valid rule selection. If <select> is True, highlight that selection. """
        node = selection = None
        if index:
            node = self._formatter.node_at(index)
            selection = self._nodes_by_rule.get(node)
        elif rule:
            node = self._rules_by_node.get(rule)
            if node is not None:
                selection = rule
        return self._formatter.to_html(node, select), selection


class GraphRenderer(LX):

    def LXGraphGenerate(self, rule:StenoRule, *, recursive:bool=True, compressed:bool=True,
                        ref:str="", prev:StenoRule=None, select:bool=False) -> Tuple[str, Optional[StenoRule]]:
        graph = self._generate(rule, recursive, compressed)
        return graph.render(ref, prev, select)

    @lru_cache(maxsize=256)
    def _generate(self, rule:StenoRule, *args):
        """ Generate a graph object. This isn't cheap, so the most recent ones are cached. """
        layout = self.LAYOUT
        return StenoGraph(rule, layout.SEP, layout.SPLIT, *args)
