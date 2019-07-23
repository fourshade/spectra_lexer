""" Base module for text graphing. Defines top-level graph classes and structures. """

from functools import lru_cache
from typing import Dict, Optional, Tuple

from .html import HTMLTextField
from .layout import CascadedGraphLayout, CompressedGraphLayout
from .node import BranchNode, GraphNode, NodeFactory, RootNode
from spectra_lexer.resource import KeyLayout, StenoRule


class StenoGraph:
    """ Class for a formatted monospaced text graph of a rule. Layouts arrange the children however they want. """

    _rules_by_node: Dict[StenoRule, GraphNode]  # Mapping of each rule to its generated node.
    _nodes_by_rule: Dict[GraphNode, StenoRule]  # Mapping of each generated node to its rule.

    _factory: NodeFactory
    _recursive: bool       # If True, also generate children of children (and so on).

    formatter: HTMLTextField  # Formats the output text based on which node is selected (if any).

    def __init__(self, factory:NodeFactory, rule:StenoRule, recursive:bool=True, compressed:bool=True):
        """ Make a node tree layout out of the given rule and parameters, tracking the node<->rule relationships. """
        self._factory = factory
        self._recursive = recursive
        root = RootNode(rule.letters)
        self._rules_by_node = {rule: root}
        self._nodes_by_rule = {root: rule}
        self._add_children(root, rule)
        # Lay out and render all text objects into character lines and node reference lists.
        layout = CompressedGraphLayout(root) if compressed else CascadedGraphLayout(root)
        lines, nodes = layout.render()
        self.formatter = HTMLTextField(lines, nodes)

    def _add_children(self, node:BranchNode, rule:StenoRule) -> None:
        """ Recursively add children from a rulemap. """
        node.add_children([self._make_node(i.rule, i.start, i.length) for i in rule.rulemap])

    def _make_node(self, rule:StenoRule, *args) -> GraphNode:
        """ Only create derived type nodes if a rule has children and we are allowed to draw them. """
        if rule.rulemap and self._recursive:
            node = self._factory.make_derived(rule, *args)
            self._add_children(node, rule)
        else:
            node = self._factory.make_base(rule, *args)
        # Keep track of the node and its rule in case we need one from the other.
        self._rules_by_node[rule] = node
        self._nodes_by_rule[node] = rule
        return node

    def render(self, index:str="", rule:StenoRule=None, select:bool=False) -> Tuple[str, Optional[StenoRule]]:
        """ Process and render a graph as HTML text with a section index and/or specific rule selected.
            Return the finished text and any valid rule selection. If <select> is True, highlight that selection. """
        node = selection = None
        if index:
            node = self.formatter.node_at(index)
            selection = self._nodes_by_rule.get(node)
        elif rule:
            node = self._rules_by_node.get(rule)
            if node is not None:
                selection = rule
        return self.formatter.to_html(node, select), selection


class GraphGenerator:
    """ High-level graph generator class, directly below the main component. """

    _factory: NodeFactory

    def __init__(self, layout:KeyLayout):
        self._factory = NodeFactory(layout.SEP, layout.SPLIT)

    @lru_cache(maxsize=256)
    def __call__(self, rule:StenoRule, **kwargs) -> StenoGraph:
        """ Generate a graph object. This isn't cheap, so the most recent ones are cached. """
        return StenoGraph(self._factory, rule, **kwargs)
