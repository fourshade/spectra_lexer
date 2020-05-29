from typing import Dict, List, Sequence

from spectra_lexer.board.element import BoardElementFactory
from spectra_lexer.board.factory import BoardDiagram, BoardFactory, BoardRule
from spectra_lexer.board.tfrm import GridLayoutEngine
from spectra_lexer.graph import GraphNode, IBody, IConnectors, TextElementCanvas
from spectra_lexer.graph.body import BoldBody, SeparatorBody, ShiftedBody, StandardBody
from spectra_lexer.graph.connectors import InversionConnectors, LinkedConnectors, NullConnectors, \
                                           SimpleConnectors, ThickConnectors, UnmatchedConnectors
from spectra_lexer.graph.format import BaseHTMLFormatter, CompatHTMLFormatter, StandardHTMLFormatter
from spectra_lexer.graph.layout import CascadedLayoutEngine, CompressedLayoutEngine
from spectra_lexer.resource.board import StenoBoardDefinitions
from spectra_lexer.resource.keys import StenoKeyLayout
from spectra_lexer.resource.rules import StenoRule


class BoardEngine:
    """ Returns steno board diagrams corresponding to key strings and/or steno rules. """

    def __init__(self, keymap:StenoKeyLayout, factory:BoardFactory) -> None:
        self._to_skeys = keymap.rtfcre_to_skeys  # Converts user RTFCRE steno strings to s-keys.
        self._factory = factory
        self._id_cache = {}

    def _to_board_rule(self, rule:StenoRule) -> BoardRule:
        r_id = rule.id
        if r_id and r_id in self._id_cache:
            return self._id_cache[r_id]
        skeys = self._to_skeys(rule.keys)
        letters = rule.letters
        alt_text = rule.alt
        children = [self._to_board_rule(item.child) for item in rule]
        br = BoardRule(skeys, letters, alt_text, children)
        br.is_linked = rule.is_linked
        br.is_inversion = rule.is_inversion
        br.is_unmatched = rule.is_unmatched
        br.is_rare = rule.is_rare
        br.is_stroke = rule.is_stroke
        br.is_word = rule.is_word
        if r_id:
            self._id_cache[r_id] = br
        return br

    def draw_keys(self, keys:str, aspect_ratio:float=None) -> BoardDiagram:
        """ Generate a board diagram from a steno key string arranged according to <aspect ratio>. """
        skeys = self._to_skeys(keys)
        return self._factory.draw_keys(skeys, aspect_ratio)

    def draw_rule(self, rule:StenoRule, aspect_ratio:float=None, *, show_letters=True) -> BoardDiagram:
        """ Generate a board diagram from a steno rule object arranged according to <aspect ratio>. """
        br = self._to_board_rule(rule)
        return self._factory.draw_rule(br, aspect_ratio, show_letters=show_letters)


def build_board_engine(keymap:StenoKeyLayout, board_defs:StenoBoardDefinitions) -> BoardEngine:
    """ Generate board diagram elements with the background of every key to use as a diagram base. """
    elem_factory = BoardElementFactory(board_defs.offsets, board_defs.shapes, board_defs.glyphs)
    layout = GridLayoutEngine(**board_defs.bounds)
    key_sep = keymap.separator_key()
    key_special = keymap.special_key()
    key_procs = board_defs.keys
    key_procs[key_sep] = ["sep=1"]
    rule_procs = board_defs.rules
    factory = BoardFactory(elem_factory, layout, key_special, key_procs, rule_procs)
    return BoardEngine(keymap, factory)


class RuleGraph:
    """ A self-contained object to draw text graphs of a steno rule and optionally highlight any descendant. """

    def __init__(self, ref_map:Dict[str, StenoRule], formatter:BaseHTMLFormatter) -> None:
        self._ref_map = ref_map
        self._formatter = formatter

    def refs(self) -> List[str]:
        """ Return a list of ref strings for each descendant. """
        return list(self._ref_map)

    def get_rule(self, ref:str) -> StenoRule:
        """ Return the rule mapped to this ref string. """
        return self._ref_map[ref]

    def draw(self, ref="", *, intense=False) -> str:
        """ Return an HTML text graph with <ref> highlighted.
            Highlight nothing if <ref> is blank. Use brighter highlighting colors if <intense> is True. """
        return self._formatter.format(ref, intense)


class GraphEngine:
    """ Creates trees of displayable graph nodes out of steno rules. """

    def __init__(self, key_sep:str, ignored_chars="") -> None:
        self._key_sep = key_sep
        self._ignored = set(ignored_chars)  # Tokens to ignore at the beginning of key strings (usually the hyphen).

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

    def _build_tree(self, ref_dict:Dict[str, StenoRule], rule:StenoRule, start:int, length:int) -> GraphNode:
        """ Build a display node tree recursively. """
        children = [self._build_tree(ref_dict, c.child, c.start, c.length) for c in rule]
        ref = str(len(ref_dict))
        ref_dict[ref] = rule
        return self._build_node(ref, rule, start, length, children)

    def graph(self, rule:StenoRule, *, compressed=True, compat=False) -> RuleGraph:
        """ Generate a graph object for a steno rule.
            The root node's attach points are arbitrary, so start=0 and length=len(letters). """
        ref_dict = {}
        root = self._build_tree(ref_dict, rule, 0, len(rule.letters))
        layout_engine = CompressedLayoutEngine() if compressed else CascadedLayoutEngine()
        layout = layout_engine.layout(root)
        grid = TextElementCanvas.from_layout(layout).to_grid()
        formatter = CompatHTMLFormatter(grid) if compat else StandardHTMLFormatter(grid)
        return RuleGraph(ref_dict, formatter)
