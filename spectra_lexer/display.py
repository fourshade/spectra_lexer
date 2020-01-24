from functools import lru_cache
from typing import Dict, List, Sequence

from spectra_lexer.board import BoardDiagram, BoardDocumentFactory, BoardElementFactory, \
    BoardElementGroup, SVGElementFactory
from spectra_lexer.graph import IBody, BoldBody, SeparatorBody, ShiftedBody, StandardBody, GraphNode, IConnectors, \
    InversionConnectors, LinkedConnectors, NullConnectors, SimpleConnectors, ThickConnectors, UnmatchedConnectors, \
    CascadedLayoutEngine,  CompressedLayoutEngine, ElementCanvas, \
    BaseHTMLFormatter, CompatHTMLFormatter, StandardHTMLFormatter
from spectra_lexer.resource.board import StenoBoardDefinitions
from spectra_lexer.resource.keys import StenoKeyConverter
from spectra_lexer.resource.rules import StenoRule


class DisplayNode(GraphNode):
    """ Adds a rule reference to a standard node. """

    def __init__(self, rule:StenoRule, *args) -> None:
        self.rule = rule
        super().__init__(*args)


class DisplayNodeFactory:
    """ Creates displayable graph nodes out of steno rules. """

    def __init__(self, ignored_chars="") -> None:
        self._ignored = set(ignored_chars)  # Tokens to ignore at the beginning of key strings (usually the hyphen).

    def build_tree(self, rule:StenoRule) -> DisplayNode:
        """ The root node's attach points are arbitrary, so tstart=0 and tlen=len(letters). """
        return self._build_tree(rule, 0, len(rule.letters))

    def _build_tree(self, rule:StenoRule, start:int, length:int) -> DisplayNode:
        """ Build a display node tree recursively. """
        children = [self._build_tree(c.child, c.start, c.length) for c in rule]
        return self.build_node(rule, start, length, children)

    def build_node(self, rule:StenoRule, start:int, length:int, children:Sequence[DisplayNode]=()) -> DisplayNode:
        """ Make a new node from a rule's properties, position, and descendants. """
        body = self._build_body(rule)
        width = body.width()
        connectors = self._build_connectors(rule, length, width)
        return DisplayNode(rule, body, connectors, start, length, children)

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


class BoardElementIndex:
    """ Returns steno board elements corresponding to key strings and/or steno rules.
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

    def __init__(self, converter:StenoKeyConverter, combo_key:str, factory:BoardElementFactory,
                 key_procs:Dict[str, List[str]], rule_procs:Dict[str, List[str]]) -> None:
        self._to_skeys = converter.rtfcre_to_skeys  # Converts user RTFCRE steno strings to s-keys.
        self._combo_key = combo_key                 # Key used with others without contributing to text.
        self._factory = factory
        self._key_procs = key_procs
        self._rule_procs = rule_procs

    def base_elems(self) -> List[BoardElementGroup]:
        """ Generate board diagram elements with the background of every key to use as a diagram base. """
        return [self._factory.processed_group(procs[:-1], self.FILL_BASE) for procs in self._key_procs.values()]

    def elems_from_keys(self, rule:StenoRule) -> List[BoardElementGroup]:
        """ Generate board diagram elements from a rule's keys without any special shapes or colors. """
        skeys = self._to_skeys(rule.keys)
        return self._elems_from_skeys(skeys)[:]

    def elems_from_rule(self, rule:StenoRule, show_letters:bool) -> List[BoardElementGroup]:
        """ Generate board diagram elements from a steno rule object. Copy the list to avoid corrupting the caches. """
        return self._elems_from_rule(rule, show_letters)[:]

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

    @lru_cache(maxsize=None)
    def _elems_from_skeys(self, skeys:str, bg:str=None) -> List[BoardElementGroup]:
        """ Generate board diagram elements from a set of steno s-keys. """
        return [self._factory.processed_group(self._key_procs[s], bg or self.FILL_MATCHED)
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
                return [*elems, self._factory.processed_group(procs, bg or self.FILL_RULE, letters)]
            elif alt_text:
                return [*elems, self._factory.processed_group(procs, bg or self.FILL_ALT, alt_text)]
        return []

    def _elems_from_linked(self, rule:StenoRule, show_letters:bool, bg:str=None) -> List[BoardElementGroup]:
        """ A rule using linked strokes must follow this pattern: (.first)(~/~)(last.) """
        strokes = [self._elems_from_rule(item.child, show_letters, bg) for item in rule]
        return [self._factory.linked_group(strokes[0], strokes[-1])]

    def _elems_from_inversion(self, rule:StenoRule, show_letters:bool, bg:str=None) -> List[BoardElementGroup]:
        """ A rule using inversion connects the first two elements with arrows. """
        grps = []
        for item in rule:
            grps += self._elems_from_rule(item.child, show_letters, bg)
        return [self._factory.inversion_group(grps)]


class BoardFactory:
    """ Creates visual representations of steno strokes. """

    def __init__(self, element_index:BoardElementIndex, doc_factory:BoardDocumentFactory) -> None:
        self._element_index = element_index
        self._doc_factory = doc_factory

    def build(self, rule:StenoRule, aspect_ratio:float=None, show_compound=True, show_letters=True) -> BoardDiagram:
        """ Generate an encoded board diagram layout arranged according to <aspect ratio>. """
        if show_compound:
            elems = self._element_index.elems_from_rule(rule, show_letters)
        else:
            elems = self._element_index.elems_from_keys(rule)
        return self._doc_factory.make_svg(elems, aspect_ratio)

    @classmethod
    def from_resources(cls, converter:StenoKeyConverter,
                       board_defs:StenoBoardDefinitions, combo_key:str) -> "BoardFactory":
        svg_factory = SVGElementFactory()
        elem_factory = BoardElementFactory(svg_factory, board_defs.offsets, board_defs.shapes, board_defs.glyphs)
        elem_index = BoardElementIndex(converter, combo_key, elem_factory, board_defs.keys, board_defs.rules)
        base_elems = elem_index.base_elems()
        defs_base = elem_factory.base_group(*base_elems)
        doc_factory = BoardDocumentFactory(svg_factory, *defs_base, *board_defs.bounds)
        return cls(elem_index, doc_factory)


class DisplayOptions:
    """ Namespace for steno display options. """

    board_aspect_ratio: float = None        # Aspect ratio for board viewing area (None means pure horizontal layout).
    board_show_compound: bool = True        # Show compound keys on board with alt labels (i.e. F instead of TP).
    board_show_letters: bool = True         # Show letters on board when possible. Letters override alt labels.
    graph_compressed_layout: bool = True    # Compress the graph layout vertically to save space.
    graph_compatibility_mode: bool = False  # Force correct spacing in the graph using HTML tables.


class DisplayPage:
    """ Data class that contains an HTML formatted graph, a caption, an SVG board, and a rule ID reference. """

    def __init__(self, graph:str, intense_graph:str, caption:str, board:BoardDiagram, rule_id="") -> None:
        self.graph = graph                  # HTML text graph for this selection.
        self.intense_graph = intense_graph  # Brighter HTML text graph for this selection.
        self.caption = caption              # Text characters drawn as a caption (possibly on a tooltip).
        self.board = board                  # XML string containing this rule's SVG board diagram.
        self.rule_id = rule_id              # If the selection uses a valid rule, its rule ID, else an empty string.


class DisplayData:
    """ Data class that contains graphical data for an entire analysis. """

    def __init__(self, keys:str, letters:str, pages:Dict[str, DisplayPage], default_page:DisplayPage) -> None:
        self.keys = keys                  # Translation keys in RTFCRE.
        self.letters = letters            # Translation letters.
        self.pages_by_ref = pages         # Analysis pages keyed by HTML anchor reference.
        self.default_page = default_page  # Default starting analysis page. May also be included in pages_by_ref.


class DisplayEngine:
    """ Creates visual representations of steno analyses. """

    def __init__(self, node_factory:DisplayNodeFactory, board_factory:BoardFactory) -> None:
        self._node_factory = node_factory
        self._board_factory = board_factory

    def process(self, analysis:StenoRule, options=DisplayOptions()) -> DisplayData:
        """ Process a steno rule (usually a lexer analysis) into graphs and boards for the GUI. """
        keys = analysis.keys
        letters = analysis.letters
        root = self._node_factory.build_tree(analysis)
        formatter = self._build_formatter(root, options.graph_compressed_layout, options.graph_compatibility_mode)
        # Iterate over the root node and render all its descendants depth-first recursively.
        pages = {}
        node_list = [root]
        for node in node_list:
            node_list += node.children()
            ref = node.ref()
            ngraph, igraph = [formatter.format(ref, intense) for intense in (False, True)]
            # Make a caption to display above the board diagram for this rule.
            rule = node.rule
            if rule is analysis:
                # The root translation is in the title bar. Show only the info string in its caption.
                caption = rule.info
            elif rule and rule.letters:
                # Compound rules show the complete mapping of keys to letters in their caption.
                caption = f'{rule}: {rule.info}'
            else:
                # Base rules display only their keys to the left of their descriptions.
                caption = f"{rule.keys}: {rule.info}"
            xml = self._board_factory.build(rule, options.board_aspect_ratio,
                                            options.board_show_compound, options.board_show_letters)
            pages[ref] = DisplayPage(ngraph, igraph, caption, xml, rule.id)
        # When nothing is selected, use the board and caption for the root node.
        root_page = pages[root.ref()]
        default_graph = formatter.format()
        default_page = DisplayPage(default_graph, default_graph, root_page.caption, root_page.board)
        return DisplayData(keys, letters, pages, default_page)

    @staticmethod
    def _build_formatter(root:DisplayNode, compressed=True, compat=False) -> BaseHTMLFormatter:
        layout_engine = CompressedLayoutEngine() if compressed else CascadedLayoutEngine()
        layout = layout_engine.layout(root)
        grid = ElementCanvas.from_layout(layout)
        formatter = CompatHTMLFormatter(grid) if compat else StandardHTMLFormatter(grid)
        return formatter

    @classmethod
    def from_resources(cls, converter:StenoKeyConverter, board_defs:StenoBoardDefinitions,
                       ignored_chars:str, combo_key:str) -> "DisplayEngine":
        node_factory = DisplayNodeFactory(ignored_chars)
        board_factory = BoardFactory.from_resources(converter, board_defs, combo_key)
        return cls(node_factory, board_factory)
