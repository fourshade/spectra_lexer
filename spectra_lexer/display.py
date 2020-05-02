from functools import lru_cache
from typing import Dict, List, Sequence

from spectra_lexer.board import BoardDiagram, BoardDimensions, BoardDocumentFactory, BoardElementFactory, \
    BoardElementGroup, SVGElementFactory
from spectra_lexer.graph import IBody, BoldBody, SeparatorBody, ShiftedBody, StandardBody, GraphNode, IConnectors, \
    InversionConnectors, LinkedConnectors, NullConnectors, SimpleConnectors, ThickConnectors, UnmatchedConnectors, \
    CascadedLayoutEngine,  CompressedLayoutEngine, ElementCanvas, \
    BaseHTMLFormatter, CompatHTMLFormatter, StandardHTMLFormatter
from spectra_lexer.resource.board import StenoBoardDefinitions
from spectra_lexer.resource.keys import StenoKeyConverter
from spectra_lexer.resource.rules import StenoRule


class BoardFactory:
    """ Returns steno board diagrams corresponding to key strings and/or steno rules.
        The main dict contains of a list of strings for each shape of board element.
        Each of these strings defines a "proc": a process that positions and/or constructs SVG elements.
        Execution involves running every proc in the list, in order. """

    FILL_BASE = "#7F7F7F"
    FILL_MATCHED = "#007FFF"
    FILL_UNMATCHED = "#DFDFDF"
    FILL_RULE = "#00AFFF"
    FILL_RARE = "#9FCFFF"
    FILL_COMBO = "#7F7FFF"
    FILL_NUMBER = "#3F9F00"
    FILL_SYMBOL = "#AFAF00"
    FILL_SPELLING = "#7F7FFF"
    FILL_BRIEF = "#FF7F00"
    FILL_ALT = "#00AFAF"

    def __init__(self, converter:StenoKeyConverter, combo_key:str, elem_factory:BoardElementFactory,
                 key_procs:Dict[str, List[str]], rule_procs:Dict[str, List[str]],
                 doc_factory:BoardDocumentFactory) -> None:
        self._to_skeys = converter.rtfcre_to_skeys  # Converts user RTFCRE steno strings to s-keys.
        self._combo_key = combo_key                 # Key used with others without contributing to text.
        self._elem_factory = elem_factory
        self._key_procs = key_procs
        self._rule_procs = rule_procs
        self._doc_factory = doc_factory

    @lru_cache(maxsize=None)
    def _elems_from_skeys(self, skeys:str, bg:str=None) -> List[BoardElementGroup]:
        """ Generate board diagram elements from a set of steno s-keys. """
        return [self._elem_factory.processed_group(self._key_procs[s], bg or self.FILL_MATCHED)
                for s in skeys if s in self._key_procs]

    @lru_cache(maxsize=None)
    def _elems_from_rule_info(self, skeys:str, letters:str, alt_text:str, bg:str=None) -> List[BoardElementGroup]:
        """ Generate board diagram elements from a rule's properties if procs using its s-keys exist. """
        elems = []
        procs = self._rule_procs.get(skeys)
        ck = self._combo_key
        if procs is None and ck in skeys and ck != skeys:
            # Rules using the star should have that key separate from their text.
            leftover = skeys.replace(ck, "")
            bg = self.FILL_COMBO
            elems += self._elems_from_skeys(ck, bg)
            procs = self._rule_procs.get(leftover)
        if procs is not None:
            if letters:
                return [*elems, self._elem_factory.processed_group(procs, bg or self.FILL_RULE, letters)]
            elif alt_text:
                return [*elems, self._elem_factory.processed_group(procs, bg or self.FILL_ALT, alt_text)]
        return []

    def _elems_from_linked(self, rule:StenoRule, show_letters:bool, bg:str=None) -> List[BoardElementGroup]:
        """ A rule using linked strokes must follow this pattern: (.first)(~/~)(last.) """
        strokes = [self._elems_from_rule(item.child, show_letters, bg) for item in rule]
        return [self._elem_factory.linked_group(strokes[0], strokes[-1])]

    def _elems_from_inversion(self, rule:StenoRule, show_letters:bool, bg:str=None) -> List[BoardElementGroup]:
        """ A rule using inversion connects the first two elements with arrows. """
        grps = []
        for item in rule:
            grps += self._elems_from_rule(item.child, show_letters, bg)
        return [self._elem_factory.inversion_group(grps)]

    def _elems_from_rule(self, rule:StenoRule, show_letters:bool, bg:str=None) -> List[BoardElementGroup]:
        """ Generate board diagram elements from a steno rule recursively. Propagate any background colors. """
        skeys = self._to_skeys(rule.keys)
        letters = rule.letters
        alt_text = rule.alt
        if letters and not any(map(str.isalpha, letters)):
            bg = self.FILL_SYMBOL if not any(map(str.isdigit, letters)) else self.FILL_NUMBER
            if not alt_text:
                alt_text = letters
        if rule.is_linked:
            return self._elems_from_linked(rule, show_letters, bg)
        elif rule.is_inversion:
            return self._elems_from_inversion(rule, show_letters, bg)
        elif rule.is_unmatched:
            return self._elems_from_skeys(skeys, self.FILL_UNMATCHED)
        elif rule.is_rare:
            bg = self.FILL_RARE
        elif rule.is_stroke:
            bg = self.FILL_SPELLING
        elif rule.is_word:
            bg = self.FILL_BRIEF
        elems = self._elems_from_rule_info(skeys, letters if show_letters else "", alt_text, bg)
        if elems:
            return elems
        elif rule:
            # Add elements recursively from all child rules.
            return [elem for item in rule for elem in self._elems_from_rule(item.child, show_letters, bg)]
        # There may not be compound elements for everything; in that case, use elements for each raw key.
        return self._elems_from_skeys(skeys)

    def _make_svg(self, elems:List[BoardElementGroup], aspect_ratio:float=None) -> BoardDiagram:
        return self._doc_factory.make_svg(elems, aspect_ratio)

    def board_from_keys(self, keys:str, aspect_ratio:float=None) -> BoardDiagram:
        """ Generate a board diagram from a steno key string arranged according to <aspect ratio>.
            Copy the element list to avoid corrupting the caches. """
        skeys = self._to_skeys(keys)
        elems = self._elems_from_skeys(skeys)[:]
        return self._make_svg(elems, aspect_ratio)

    def board_from_rule(self, rule:StenoRule, aspect_ratio:float=None, *, show_letters=True) -> BoardDiagram:
        """ Generate a board diagram from a steno rule object arranged according to <aspect ratio>.
            Copy the element list to avoid corrupting the caches. """
        elems = self._elems_from_rule(rule, show_letters)[:]
        return self._make_svg(elems, aspect_ratio)

    @classmethod
    def from_resources(cls, converter:StenoKeyConverter,
                       board_defs:StenoBoardDefinitions, combo_key:str) -> "BoardFactory":
        """ Generate board diagram elements with the background of every key to use as a diagram base. """
        svg_factory = SVGElementFactory()
        elem_factory = BoardElementFactory(svg_factory, board_defs.offsets, board_defs.shapes, board_defs.glyphs)
        base_groups = [elem_factory.processed_group(procs[:-1], cls.FILL_BASE) for procs in board_defs.keys.values()]
        defs, base = elem_factory.base_pair(base_groups)
        dims = BoardDimensions(*board_defs.bounds)
        doc_factory = BoardDocumentFactory(svg_factory, defs, base, dims)
        return cls(converter, combo_key, elem_factory, board_defs.keys, board_defs.rules, doc_factory)


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


class GraphFactory:
    """ Creates trees of displayable graph nodes out of steno rules. """

    def __init__(self, ignored_chars="") -> None:
        self._ignored = set(ignored_chars)  # Tokens to ignore at the beginning of key strings (usually the hyphen).

    def _build_body(self, rule:StenoRule) -> IBody:
        """ Make a node display body. The text is shifted left if it starts with an ignored token. """
        keys = rule.keys
        if rule:
            body = BoldBody(rule.letters)
        elif rule.is_separator:
            body = SeparatorBody(keys)
        elif keys[:1] in self._ignored:
            body = ShiftedBody(keys, -1)
        else:
            body = StandardBody(keys)
        return body

    @staticmethod
    def _build_connectors(rule:StenoRule, length:int, width:int) -> IConnectors:
        """ Make a node connector set based on the rule type. """
        if rule.is_inversion:
            # Node for an inversion of steno order. Connectors should indicate some kind of "reversal".
            connectors = InversionConnectors(length, width)
        elif rule.is_linked:
            # Node for a child rule that uses keys from two strokes. This complicates stroke delimiting.
            connectors = LinkedConnectors(length, width)
        elif rule:
            connectors = ThickConnectors(length, width)
        elif rule.is_separator:
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

    def build(self, rule:StenoRule, *, compressed=True, compat=False) -> RuleGraph:
        """ Generate a graph object for a steno rule.
            The root node's attach points are arbitrary, so start=0 and length=len(letters). """
        ref_dict = {}
        root = self._build_tree(ref_dict, rule, 0, len(rule.letters))
        layout_engine = CompressedLayoutEngine() if compressed else CascadedLayoutEngine()
        layout = layout_engine.layout(root)
        grid = ElementCanvas.from_layout(layout)
        formatter = CompatHTMLFormatter(grid) if compat else StandardHTMLFormatter(grid)
        return RuleGraph(ref_dict, formatter)
