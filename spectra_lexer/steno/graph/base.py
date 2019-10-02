""" Base module for text graphing. Defines top-level graph structures. """

from typing import List, Optional, Tuple, TypeVar

from .layout import BaseGraphLayout, CascadedGraphLayout, CompressedGraphLayout
from .node import GraphNode, NodeFactory
from .render import Canvas, BaseHTMLFormatter, CompatHTMLFormatter, StandardHTMLFormatter
from ..rules import StenoRule


class NodeIndex:
    """ Index for matching ref strings and rules to their nodes. """

    _NODE = TypeVar("_NODE")

    def __init__(self) -> None:
        self._nodes_by_ref = {}   # Mapping of ref strings to nodes in sequential order of creation.
        self._refs_by_node = {}   # Mapping of nodes back to ref string.
        self._nodes_by_name = {}  # Mapping of each rule's name to the node that used it last.
        self._rules_by_node = {}  # Mapping of each generated node to its rule.

    def add(self, rule:StenoRule, node:_NODE) -> None:
        """ Add a new node <-> rule mapping. """
        ref = str(len(self._nodes_by_ref))
        self._nodes_by_ref[ref] = node
        self._refs_by_node[node] = ref
        self._nodes_by_name[rule.name] = node
        self._rules_by_node[node] = rule

    def node_from_ref(self, ref:str) -> Optional[_NODE]:
        return self._nodes_by_ref.get(ref)

    def ref_from_node(self, node:_NODE) -> Optional[str]:
        return self._refs_by_node.get(node)

    def node_from_rule_name(self, rule_name:str) -> Optional[_NODE]:
        """ Return the last recorded node that matches <rule_name>, if any. """
        return self._nodes_by_name.get(rule_name)

    def rule_from_node(self, node:_NODE) -> Optional[StenoRule]:
        """ Return the rule from which <node> was built. """
        return self._rules_by_node.get(node)


class TreeBuilder:

    def __init__(self, factory:NodeFactory, index:NodeIndex, max_depth:int) -> None:
        self._factory = factory
        self._index = index
        self._max_depth = max_depth

    def build(self, rule:StenoRule) -> GraphNode:
        """ The root node's attach points are arbitrary, so tstart=0 and tlen=blen. """
        return self._build_recursive(rule, 0, len(rule.letters), 0)

    def _build_recursive(self, rule:StenoRule, start:int, length:int, depth:int) -> GraphNode:
        """ Make a child node from a rulemap item. Only create one level of children if recursion is not allowed. """
        rulemap = rule.rulemap
        children = []
        if depth <= self._max_depth:
            for item in rulemap:
                child = self._build_recursive(item.rule, item.start, item.length, depth + 1)
                children.append(child)
        node = self._factory.make_node(rule, start, length, depth, children)
        self._index.add(rule, node)
        return node


class StenoGraph:
    """ Formats and renders a monospaced text graph of a rule. """

    def __init__(self, root:GraphNode, layout:BaseGraphLayout, index:NodeIndex, formatter:BaseHTMLFormatter):
        self._root = root
        self._layout = layout
        self._index = index          # Index with every node created.
        self._formatter = formatter  # Formats the output text based on which node is selected (if any).

    def render(self, ref="", *, find_rule=False, **kwargs) -> Tuple[str, Optional[StenoRule]]:
        """ Render a graph as HTML text with an optional reference node selected.
            <ref> is a rule name if <find_rule> is True; otherwise it is an anchor href.
            Return the finished text and any valid rule selection. """
        if find_rule:
            node = self._index.node_from_rule_name(ref)
        else:
            ref = self._formatter.href_to_ref(ref)
            node = self._index.node_from_ref(ref)
        text = self._render(node, **kwargs)
        rule = self._index.rule_from_node(node)
        return text, rule

    def _render(self, target:GraphNode, *, intense=False) -> str:
        """ Format a node graph and highlight a node ancestry line, starting with the root down to some terminal node.
            If <ancestry> is empty, highlight nothing. If <ancestry> is the root, highlight it (and only it) entirely.
            Otherwise, only highlight columns the root shares with the terminal node. """
        root = self._root
        *_, height, width, items = root.layout(self._layout)
        canvas = Canvas(height, width, self._formatter)
        items = [(root, 0, 0, items)]
        self._render_recursive(canvas, 0, 0, items, target, intense)
        return str(canvas)

    def _render_recursive(self, canvas:Canvas, parent_row:int, parent_col:int,
                          items:List[tuple], target:GraphNode, intense:bool) -> None:
        """ Render each item on the canvas with respect to its parent. """
        for child, row, col, c_items in items:
            this_row = parent_row + row
            this_col = parent_col + col
            if c_items:
                self._render_recursive(canvas, this_row, this_col, c_items, target, intense)
            ref = self._index.ref_from_node(child)
            child.write(canvas, parent_row, this_row, this_col, ref, intense, target)


class GraphEngine:
    """ Creates text graphs and fills indices matching these rules to their nodes. """

    def __init__(self) -> None:
        self._factory = NodeFactory()

    def generate(self, rule:StenoRule, recursive=True, compressed=True, compat=False):
        """ Make a root graph node and formatter out of <rule> and construct a graph object.
            <recursive> - If True, add sub-graphs for rules that are composed of other rules.
            <compressed> - If True, lay out the graph in a manner that squeezes nodes together as much as possible.
            <compat> - If True, use a formatter that implements text monospacing with explicit markup. """
        index = NodeIndex()
        max_depth = 10 if recursive else 1
        builder = TreeBuilder(self._factory, index, max_depth)
        root = builder.build(rule)
        layout = CompressedGraphLayout() if compressed else CascadedGraphLayout()
        formatter = CompatHTMLFormatter() if compat else StandardHTMLFormatter()
        return StenoGraph(root, layout, index, formatter)
