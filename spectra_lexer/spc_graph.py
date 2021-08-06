from typing import Container, Dict, Iterator, Mapping

from spectra_lexer.graph.body import BoldBody, IBody, SeparatorBody, ShiftedBody, StandardBody
from spectra_lexer.graph.connectors import IConnectors, InversionConnectors, LinkedConnectors, NullConnectors, \
    SimpleConnectors, ThickConnectors, UnmatchedConnectors
from spectra_lexer.graph.format import HTML_COMPAT, HTML_STANDARD, TextElementGrid
from spectra_lexer.graph.layout import CascadedGraphLayout, CompressedGraphLayout
from spectra_lexer.graph.node import GraphNode
from spectra_lexer.resource.rules import StenoRule

HTMLGraph = str                        # Marker type for an HTML text graph.
RuleMapping = Mapping[str, StenoRule]  # Mapping of graph reference strings to steno rules.


class GraphTree(RuleMapping):
    """ A self-contained object to draw text graphs of a steno rule and optionally highlight any descendant.
        Implements the mapping protocol for ref strings to steno rules. """

    def __init__(self, tree_map:RuleMapping, grid:TextElementGrid) -> None:
        self._tree_map = tree_map
        self._grid = grid

    def __len__(self) -> int:
        return len(self._tree_map)

    def __iter__(self) -> Iterator[str]:
        return iter(self._tree_map)

    def __getitem__(self, k:str) -> StenoRule:
        return self._tree_map[k]

    def draw(self, ref="", *, intense=False, compat=False) -> HTMLGraph:
        """ Return an HTML text graph with <ref> highlighted.
            Highlight nothing if <ref> is blank. Use brighter highlighting colors if <intense> is True. """
        formatter = HTML_COMPAT if compat else HTML_STANDARD
        return formatter.format(self._grid, ref, intense=intense)


class GraphEngine:
    """ Creates trees of displayable graph nodes out of steno rules. """

    def __init__(self, key_sep:str, ignored_chars:Container[str]) -> None:
        self._key_sep = key_sep        # Stroke separator key.
        self._ignored = ignored_chars  # Characters to ignore at the beginning of key strings (usually the hyphen).

    def _build_body(self, rule:StenoRule) -> IBody:
        """ Make a node display body. The text is shifted left if it starts with an ignored token. """
        keys = rule.keys
        if rule.rulemap:
            body = BoldBody(rule.letters)
        elif keys == self._key_sep:
            body = SeparatorBody(keys)
        elif keys[:1] in self._ignored:
            body = ShiftedBody(keys, -1)
        else:
            body = StandardBody(keys)
        return body

    def _build_connectors(self, rule:StenoRule, length:int, width:int) -> IConnectors:
        """ Make a node connector set based on the rule type. """
        if rule.is_inversion:
            # Node for an inversion of steno order. Connectors should indicate some kind of "reversal".
            connectors = InversionConnectors(length, width)
        elif rule.is_split:
            # Node for a child rule that uses keys from two strokes. This complicates stroke delimiting.
            connectors = LinkedConnectors(length, width)
        elif rule.rulemap:
            connectors = ThickConnectors(length, width)
        elif rule.keys == self._key_sep:
            connectors = NullConnectors()
        elif rule.is_unmatched:
            connectors = UnmatchedConnectors(width)
        else:
            connectors = SimpleConnectors(length, width)
        return connectors

    def _build_tree(self, tree_map:Dict[str, StenoRule], rule:StenoRule, start:int, length:int) -> GraphNode:
        """ Build a display node tree recursively from a rule's properties, position, and descendants. """
        ref = str(len(tree_map))
        tree_map[ref] = rule
        children = [self._build_tree(tree_map, item.child, item.start, item.length) for item in rule.rulemap]
        body = self._build_body(rule)
        width = body.width()
        connectors = self._build_connectors(rule, length, width)
        return GraphNode(ref, body, connectors, start, length, children)

    def graph(self, rule:StenoRule, *, compressed=True) -> GraphTree:
        """ Generate a graph object for a steno rule.
            The root node's attach points are arbitrary, so start=0 and length=len(letters). """
        tree_map = {}
        root = self._build_tree(tree_map, rule, 0, len(rule.letters))
        layout = CompressedGraphLayout() if compressed else CascadedGraphLayout()
        grid = root.render(layout)
        return GraphTree(tree_map, grid)
