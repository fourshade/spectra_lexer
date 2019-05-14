""" Base module for text graphing. Defines top-level graph classes and structures. """

from functools import lru_cache
from typing import Dict, Iterable, List, Optional, Tuple

from .generator import TextGenerator
from .html import HTMLTextField
from .node import GraphNode, NodeOrganizer
from ..rules import StenoRule
from ..system import LXSystem
from spectra_lexer.core import Component, Signal
from spectra_lexer.system import ConsoleCommand


class StenoGraph:
    """ Simple indexer with bounds checking for objects in a list of lists with non-uniform lengths.
        The type of objects inside the lists does not matter; only the identity/reference matters.
        Works well for text graphs (which have a relatively small number of rows and columns compared to pixels). """

    _rules_by_node: Dict[GraphNode, StenoRule]  # Mapping of each generated node to its rule.
    _grid: List[list]             # List of lists of object references in [row][col] format.
    _formatter: HTMLTextField     # Formats the output text based on which node is selected (if any).

    def __init__(self, rules:Dict[GraphNode, StenoRule], lines:List[str], nodes:List[list]):
        self._rules_by_node = rules
        self._grid = nodes
        self._formatter = HTMLTextField(lines, nodes)

    def from_character(self, row:int, col:int) -> Optional[GraphNode]:
        """ Return the node that was responsible for the graphical element at position (row, col).
            Return None if no element is there, no node owns the element, or an index is out of range. """
        if 0 <= row < len(self._grid):
            row = self._grid[row]
            if 0 <= col < len(row):
                return row[col]

    def from_rule(self, rule:StenoRule) -> Optional[GraphNode]:
        """ Given a rule, find the first node that used it (if any) in the graph. """
        for n, r in self._rules_by_node.items():
            if r is rule:
                return n

    def get_rule(self, node:GraphNode) -> Optional[StenoRule]:
        """ Given a node from the graph, look up its rule. Return None if not found. """
        return self._rules_by_node.get(node)

    def to_html(self, nodes:Iterable[GraphNode]=(), *, intense:bool=False, **kwargs) -> str:
        """ Render the graph with zero or more nodes highlighted.
            Save the text before starting and restore it to its original state after. """
        formatter = self._formatter
        formatter.save()
        formatter.start()
        for n in nodes:
            formatter.highlight(n, intense)
        text = formatter.finish()
        formatter.restore()
        return text


class LXGraph:

    @ConsoleCommand("graph_generate")
    def generate(self, rule:StenoRule, *, recursive:bool=True, compressed:bool=True, intense:bool=False,
                 locations:Iterable[Tuple[int, int]]=(), rules:Iterable[StenoRule]=()) -> Tuple[List[StenoRule], str]:
        """ Generate text graph data (of either type) from an output rule based on parameter options. """
        raise NotImplementedError

    class Output:
        @Signal
        def on_graph_output(self, graph:StenoGraph) -> None:
            raise NotImplementedError


class GraphRenderer(Component, LXGraph,
                    LXSystem.Layout):
    """ Component class for creating and formatting a monospaced text graph from a rule. """

    def generate(self, rule:StenoRule, recursive:bool=True, compressed:bool=True, **kwargs) -> tuple:
        """ Generate and send out a graph tuple. """
        graph = self._make_graph(rule, recursive, compressed)
        self.engine_call(self.Output, graph)
        return self._format_graph(graph, **kwargs)

    @lru_cache(maxsize=256)
    def _make_graph(self, rule:StenoRule, recursive:bool, compressed:bool) -> StenoGraph:
        """ Generate a graph object. This isn't cheap, so the most recent ones are cached. """
        # Make a node tree layout and mapping out of the given rule.
        organizer = NodeOrganizer(self.layout.SEP, self.layout.SPLIT, recursive)
        root = organizer.make_tree(rule)
        node_map = organizer.last_tree_mapping()
        # Generate and render all text objects into standard strings and node grids indexed by position.
        lines, nodes = TextGenerator(root, compressed).render()
        # Add everything we generated to a graph object and return it.
        graph = StenoGraph(node_map, lines, nodes)
        self.engine_call(self.Output, graph)
        return graph

    def _format_graph(self, graph:StenoGraph, *, locations:Iterable[Tuple[int, int]]=(),
                      rules:Iterable[StenoRule]=(), **kwargs) -> Tuple[List[StenoRule], str]:
        """ Get all nodes corresponding to the given locations and rules (if any) and format the graph into text. """
        nodes = _filtermap(graph.from_character, *zip(*locations))
        nodes += _filtermap(graph.from_rule, rules)
        # Get the rules associated with all selected nodes.
        rules_out = _filtermap(graph.get_rule, nodes)
        # Return a tuple with all found rules and the final formatted text with the node references highlighted.
        return rules_out, graph.to_html(nodes, **kwargs)


def _filtermap(fn, *items) -> list:
    return list(filter(None, map(fn, *items))) if items else []
