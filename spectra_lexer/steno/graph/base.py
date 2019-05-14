""" Base module for text graphing. Defines top-level graph classes and structures. """

from typing import Dict, List, Optional

from .generator import TextGenerator
from .html import HTMLTextField
from .node import GraphNode, NodeOrganizer
from spectra_lexer.resource import StenoRule


class StenoGraph:
    """ Class for a formatted monospaced text graph of a rule. """

    _rules_by_node: Dict[GraphNode, StenoRule]  # Mapping of each generated node to its rule.
    _grid: List[list]             # List of lists of object references in [row][col] format.
    _formatter: HTMLTextField     # Formats the output text based on which node is selected (if any).

    def __init__(self, rule:StenoRule, sep:str, split:str, recursive:bool, compressed:bool):
        """ Make a node tree layout and mapping out of the given rule and parameters. """
        organizer = NodeOrganizer(sep, split, recursive)
        root = organizer.make_tree(rule)
        node_map = organizer.last_tree_mapping()
        # Generate and render all text objects into standard strings and node grids indexed by position.
        lines, nodes = TextGenerator(root, compressed).render()
        # Add everything we generated to the graph object.
        self._rules_by_node = node_map
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

    def to_html(self, *nodes:GraphNode, intense:bool=False) -> str:
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
