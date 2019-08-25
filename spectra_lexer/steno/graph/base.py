""" Base module for text graphing. Defines top-level graph classes and structures. """

from typing import Optional, Tuple

from .format import CompatFormatter, HTMLFormatter
from .layout import CascadedGraphLayout, CompressedGraphLayout
from .node import NodeFactory, NodeIndex, GraphNode
from ..keys import KeyLayout
from ..rules import StenoRule


class StenoGraph:
    """ Class for a formatted monospaced text graph of a rule. Layouts arrange the children however they want. """

    _factory: NodeFactory
    index: NodeIndex
    formatter: HTMLFormatter  # Formats the output text based on which node is selected (if any).

    def __init__(self, factory:NodeFactory, rule:StenoRule, compressed:bool=True, compat:bool=False) -> None:
        """ Make a node tree layout out of the given rule and parameters, tracking the node<->rule relationships. """
        self._factory = factory
        root = factory.make_root(rule)
        self.index = NodeIndex()
        self.index.add(root, rule)
        self._make_children(root, rule)
        layout = CompressedGraphLayout(root) if compressed else CascadedGraphLayout(root)
        self.formatter = CompatFormatter(layout) if compat else HTMLFormatter(layout)

    def _make_children(self, node:GraphNode, rule:StenoRule) -> None:
        """ Make children from a rulemap and index them. """
        index_add = self.index.add
        for m_rule, start, length in rule.rulemap:
            child = self._make_node(m_rule, start, length, node)
            index_add(child, m_rule)

    def _make_node(self, rule:StenoRule, *args) -> GraphNode:
        """ Do not create derived type nodes. """
        return self._factory.make_base(rule, *args)

    def render(self, ref:str="", rule:StenoRule=None, select:bool=False) -> Tuple[str, Optional[StenoRule]]:
        """ Process and render a graph as HTML text with a section index and/or specific rule selected.
            Return the finished text and any valid rule selection. If <select> is True, highlight that selection. """
        node = selection = None
        if ref:
            node, selection = self.index.select_ref(ref)
        elif rule:
            node, selection = self.index.select_rule(rule)
        return self.formatter.to_html(node, select), selection


class RecursiveStenoGraph(StenoGraph):

    def _make_node(self, rule:StenoRule, *args) -> GraphNode:
        """ Only create derived type nodes if a rule has children. """
        if not rule.rulemap:
            return super()._make_node(rule, *args)
        node = self._factory.make_derived(rule, *args)
        self._make_children(node, rule)
        return node


class GraphGenerator:
    """ High-level graph generator class, directly below the main component. """

    _factory: NodeFactory

    def __init__(self, layout:KeyLayout) -> None:
        self._factory = NodeFactory(layout.SEP, layout.SPLIT)

    def generate(self, rule:StenoRule, recursive:bool=True, **kwargs) -> StenoGraph:
        """ Generate a text graph object from a rule. """
        cls = RecursiveStenoGraph if recursive else StenoGraph
        return cls(self._factory, rule, **kwargs)
