""" Base module for text graphing. Defines top-level graph classes and structures. """

from collections import defaultdict
from typing import List, Optional, Sequence, Tuple

from .format import CompatHTMLFormatter, HTMLFormatter
from .layout import BaseGraphLayout, CascadedGraphLayout, CompressedGraphLayout
from .render import Canvas, GraphNode, NodeFactory, IPrimitive
from ..rules import RuleMapItem, StenoRule


class NodeTree:

    def __init__(self, layout:BaseGraphLayout) -> None:
        self._layout = layout
        self._nodes = {}     # Mapping of each rule to its generated node.
        self._rules = {}     # Mapping of each generated node to its rule.
        self._ancestors = defaultdict(list)  # Mapping of each node to its ancestors in order ending with itself.
        self._children = defaultdict(list)   # Mapping of each node to its children.

    def add(self, node:GraphNode, rule:StenoRule, parent:GraphNode=None) -> None:
        self._nodes[rule] = node
        self._rules[node] = rule
        self._ancestors[node] = self._ancestors[parent] + [node]
        self._children[parent].append(node)

    def layout(self, node:GraphNode) -> List[Tuple[IPrimitive, int, int]]:
        items = []
        if node in self._children:
            children = self._children[node]
            bodies = [*map(self.layout, children)]
            params = [child.layout_params() for child in children]
            rows = self._layout.layout_rows(params)
            widths = []
            heights = []
            # Reverse the composition order to ensure that the leftmost objects get drawn last.
            for child, row, body, (col, h, w, _) in reversed([*zip(children, rows, bodies, params)]):
                if row is not None:
                    items += child.connect(row)
                    items += child.shift(body, row)
                    widths.append(col + w)
                    heights.append(row + h)
            node.resize(widths, heights)
        items.append(node.body())
        return items

    def render(self, node, row=0, col=0) -> Tuple[Canvas, int, int]:
        """ Render all primitives in order onto a grid of the calculated size. Try again with a larger one if it fails.
            Return the text, refs, and <row, col> offset required when successful. """
        s = row + col
        items = self.layout(node)
        _, h, w, _ = node.layout_params()
        canvas = Canvas(h + s, w + s)
        try:
            for (item, r, c) in items:
                item.write(canvas, row + r, col + c)
            return canvas, row, -col
        except (IndexError, ValueError):
            dim = s % 2
            return self.render(node, row + dim, col + (not dim))

    def make_refs(self) -> Tuple[dict, dict]:
        """ Generate unique HTML anchor href strings for every node descended from <root>.
            Place them in the reverse dict as well so they can be matched back to their nodes when selected. """
        hrefs = {}
        rrefs = {}
        for i, node in enumerate(self._rules):
            hrefs[node] = href = f"{i}"
            rrefs[href] = node
        return hrefs, rrefs

    def select_node(self, rule:StenoRule) -> Optional[GraphNode]:
        """ Return the first node in the tree that matches the given rule, if any. """
        return self._nodes.get(rule)

    def select_rule(self, node:GraphNode) -> Optional[StenoRule]:
        """ Return the rule for the given node in the tree. """
        return self._rules.get(node)

    def get_ancestors(self, node:GraphNode) -> Sequence[GraphNode]:
        return self._ancestors[node]


class StenoGraph:
    """ Formats and renders a monospaced text graph of a rule. """

    def __init__(self, tree:NodeTree, formatter:HTMLFormatter) -> None:
        self._tree = tree
        self._formatter = formatter  # Formats the output text based on which node is selected (if any).

    def render(self, href:str="", rule:StenoRule=None, select=False) -> Tuple[str, Optional[StenoRule]]:
        """ Process and render a graph as HTML text with an anchor href and/or specific rule selected.
            Return the finished text and any valid rule selection. If <select> is True, highlight that selection. """
        node = self._formatter.get_node(href) if rule is None else self._tree.select_node(rule)
        ancestry = self._tree.get_ancestors(node)
        text = self._formatter.to_html(ancestry, select)
        selection = self._tree.select_rule(node)
        return text, selection


class GraphGenerator(NodeFactory):
    """ Top-level factory for creating text graphs from user input. Requires minimal external resources. """

    def generate(self, rule:StenoRule, recursive=True, compressed=True, compat=False) -> StenoGraph:
        """ Make a node tree out of the given rule, tracking the node<->rule relationships.
            Generate a text graph object from this tree using a layout and formatter defined by flags. """
        # Children are recursively laid out first to determine their height and width.
        layout = CompressedGraphLayout() if compressed else CascadedGraphLayout()
        tree = NodeTree(layout)
        root = self.make_root(rule)
        tree.add(root, rule)
        self._make_nodes(rule.rulemap, tree, root, recursive)
        canvas, r, c = tree.render(root)
        hrefs, rrefs = tree.make_refs()
        formatter_cls = CompatHTMLFormatter if compat else HTMLFormatter
        formatter = formatter_cls(canvas, canvas.refs, r, c, hrefs, rrefs)
        graph = StenoGraph(tree, formatter)
        return graph

    def _make_nodes(self, rulemap:Sequence[RuleMapItem], tree:NodeTree, parent:GraphNode, recursive=True) -> None:
        """ Make nodes from a rulemap and add them to a tree. Only create their children if recursion is allowed. """
        for item in rulemap:
            rule = item.rule
            node = self.make_node(rule, item.start, item.length)
            tree.add(node, rule, parent)
            child_map = rule.rulemap
            if child_map and recursive:
                self._make_nodes(child_map, tree, node)
