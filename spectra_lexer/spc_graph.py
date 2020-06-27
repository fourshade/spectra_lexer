from typing import Iterator, List, Sequence, Tuple

from spectra_lexer.graph import GraphNode, IBody, IConnectors, TextElementCanvas
from spectra_lexer.graph.body import BoldBody, SeparatorBody, ShiftedBody, StandardBody
from spectra_lexer.graph.connectors import InversionConnectors, LinkedConnectors, NullConnectors, \
                                           SimpleConnectors, ThickConnectors, UnmatchedConnectors
from spectra_lexer.graph.format import HTMLFormatter
from spectra_lexer.graph.layout import CascadedLayoutEngine, CompressedLayoutEngine
from spectra_lexer.resource.keys import StenoKeyLayout
from spectra_lexer.resource.rules import StenoRule

# Marker type for an HTML text graph.
HTMLGraph = str


class GraphTree:
    """ A self-contained object to draw text graphs of a steno rule and optionally highlight any descendant. """

    def __init__(self, tree_listing:Sequence[StenoRule], formatter:HTMLFormatter) -> None:
        self._tree_listing = tree_listing
        self._formatter = formatter

    def iter_mappings(self) -> Iterator[Tuple[str, StenoRule]]:
        """ Yield all mappings of ref strings to steno rules in depth-first order. """
        for i, rule in enumerate(self._tree_listing):
            yield str(i), rule

    def draw(self, ref="", *, intense=False) -> HTMLGraph:
        """ Return an HTML text graph with <ref> highlighted.
            Highlight nothing if <ref> is blank. Use brighter highlighting colors if <intense> is True. """
        return self._formatter.format(ref, intense)


class GraphEngine:
    """ Creates trees of displayable graph nodes out of steno rules. """

    def __init__(self, key_sep:str, ignored_chars="") -> None:
        self._key_sep = key_sep
        self._ignored = set(ignored_chars)  # Characters to ignore at the beginning of key strings (usually the hyphen).

    def _build_body(self, rule:StenoRule) -> IBody:
        """ Make a node display body. The text is shifted left if it starts with an ignored token. """
        keys = rule.keys
        if rule:
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
        elif rule.is_linked:
            # Node for a child rule that uses keys from two strokes. This complicates stroke delimiting.
            connectors = LinkedConnectors(length, width)
        elif rule:
            connectors = ThickConnectors(length, width)
        elif rule.keys == self._key_sep:
            connectors = NullConnectors()
        elif rule.is_unmatched:
            connectors = UnmatchedConnectors(length, width)
        else:
            connectors = SimpleConnectors(length, width)
        return connectors

    def _build_node(self, ref:str, rule:StenoRule, start:int, length:int, children:Sequence[GraphNode]=()) -> GraphNode:
        """ Make a new node from a rule's properties, position, and descendants. """
        body = self._build_body(rule)
        width = body.width()
        connectors = self._build_connectors(rule, length, width)
        return GraphNode(ref, body, connectors, start, length, children)

    def _build_tree(self, tree_listing:List[StenoRule], rule:StenoRule, start:int, length:int) -> GraphNode:
        """ Build a display node tree recursively. """
        children = [self._build_tree(tree_listing, c.child, c.start, c.length) for c in rule]
        ref = str(len(tree_listing))
        tree_listing.append(rule)
        return self._build_node(ref, rule, start, length, children)

    def graph(self, rule:StenoRule, *, compressed=True, compat=False) -> GraphTree:
        """ Generate a graph object for a steno rule.
            The root node's attach points are arbitrary, so start=0 and length=len(letters). """
        tree_listing = []
        root = self._build_tree(tree_listing, rule, 0, len(rule.letters))
        layout_engine = CompressedLayoutEngine() if compressed else CascadedLayoutEngine()
        layout = layout_engine.layout(root)
        grid = TextElementCanvas.from_layout(layout).to_grid()
        formatter = HTMLFormatter(grid, compat=compat)
        return GraphTree(tree_listing, formatter)


def build_graph_engine(keymap:StenoKeyLayout) -> GraphEngine:
    key_sep = keymap.separator_key()
    ignored_chars = keymap.divider_key()
    return GraphEngine(key_sep, ignored_chars)
