""" Base module for text graphing. Defines top-level graph classes and structures. """

from functools import lru_cache
from typing import Optional, Tuple

from .format import HTMLFormatter
from .layout import CascadedGraphLayout, CompressedGraphLayout
from .node import NodeFactory, NodeIndex, GraphNode
from spectra_lexer.resource import KeyLayout, StenoRule


class StenoGraph:
    """ Class for a formatted monospaced text graph of a rule. Layouts arrange the children however they want. """

    _factory: NodeFactory
    index: NodeIndex
    formatter: HTMLFormatter  # Formats the output text based on which node is selected (if any).

    def __init__(self, factory:NodeFactory, rule:StenoRule, compressed:bool=True, **kwargs):
        """ Make a node tree layout out of the given rule and parameters, tracking the node<->rule relationships. """
        self._factory = factory
        root = factory.make_root(rule)
        self.index = NodeIndex()
        self.index.add(root, rule)
        self._add_children(root, rule.rulemap)
        layout = CompressedGraphLayout(root) if compressed else CascadedGraphLayout(root)
        self.formatter = HTMLFormatter(layout, **kwargs)

    def _add_children(self, node:GraphNode, rulemap) -> None:
        """ Recursively add children to this node from a rulemap. """
        ref_str = node.ref_str
        index_add = self.index.add
        child_append = node.children.append
        for i, (rule, start, length) in enumerate(rulemap):
            child = self._make_node(rule, start, length, node, f"{ref_str}_{i}")
            index_add(child, rule)
            child_append(child)

    def _make_node(self, *args) -> GraphNode:
        """ Do not create derived type nodes. """
        return self._factory.make_base(*args)

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
        rulemap = rule.rulemap
        if not rulemap:
            return self._factory.make_base(rule, *args)
        node = self._factory.make_derived(rule, *args)
        self._add_children(node, rulemap)
        return node


class GraphGenerator:
    """ High-level graph generator class, directly below the main component. """

    _factory: NodeFactory

    def __init__(self, layout:KeyLayout):
        self._factory = NodeFactory(layout.SEP, layout.SPLIT)

    @lru_cache(maxsize=256)
    def __call__(self, rule:StenoRule, recursive:bool=True, **kwargs) -> StenoGraph:
        """ Generate a graph object. This isn't cheap, so the most recent ones are cached. """
        cls = RecursiveStenoGraph if recursive else StenoGraph
        return cls(self._factory, rule, **kwargs)
