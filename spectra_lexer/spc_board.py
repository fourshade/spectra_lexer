from functools import lru_cache

from spectra_lexer.board.factory import BoardFactory, GroupList
from spectra_lexer.board.layout import GridLayoutEngine
from spectra_lexer.board.svg import SVGElementFactory
from spectra_lexer.board.tfrm import TextTransformer
from spectra_lexer.resource.board import StenoBoardDefinitions
from spectra_lexer.resource.keys import StenoKeyLayout
from spectra_lexer.resource.rules import StenoRule

BoardDiagram = str  # Marker type for an SVG steno board diagram.

FONT_SIZE_PX = 24  # Default font size is 24 px.


class FillColors:
    """ Namespace for background colors as HTML/SVG hex strings. """

    base = "#7F7F7F"
    matched = "#007FFF"
    unmatched = "#DFDFDF"
    letters = "#00AFFF"
    alt = "#00AFAF"
    rare = "#9FCFFF"
    combo = "#8F8FFF"
    number = "#3F8F00"
    symbol = "#AFAF00"
    spelling = "#7FFFFF"
    brief = "#FF7F00"


class BoardEngine:
    """ Returns steno board diagrams corresponding to key strings and/or steno rules. """

    def __init__(self, keymap:StenoKeyLayout, special_key:str, bg:FillColors, factory:BoardFactory) -> None:
        self._to_skeys = keymap.rtfcre_to_skeys  # Converts user RTFCRE steno strings to s-keys.
        self._special_key = special_key          # Key combined with others without contributing to text.
        self._bg = bg                            # Namespace with background colors.
        self._factory = factory                  # Factory for complete SVG board diagrams.

    def _key_groups(self, keys:str, bg:str) -> GroupList:
        skeys = self._to_skeys(keys)
        return self._factory.key_groups(skeys, bg)

    @lru_cache(maxsize=None)
    def _matched_key_groups(self, keys:str) -> GroupList:
        return self._key_groups(keys, self._bg.matched)

    @lru_cache(maxsize=None)
    def _unmatched_key_groups(self, keys:str) -> GroupList:
        return self._key_groups(keys, self._bg.unmatched)

    @lru_cache(maxsize=None)
    def _rule_groups(self, keys:str, letters:str, alt_text:str, bg:str=None) -> GroupList:
        text = letters or alt_text
        if not text:
            return []
        rbg = bg or (self._bg.letters if letters else self._bg.alt)
        skeys = self._to_skeys(keys)
        grp = self._factory.rule_group(skeys, text, rbg)
        if grp is not None:
            return [grp]
        star = self._special_key
        if star in skeys and star != skeys:
            # Rules using the star should have that key separate from their text.
            leftover = skeys.replace(star, "")
            cbg = bg or self._bg.combo
            grp = self._factory.rule_group(leftover, text, cbg)
            if grp is not None:
                return self._factory.key_groups(star, cbg) + [grp]
        return []

    def _find_groups(self, rule:StenoRule, show_letters:bool, bg:str=None) -> GroupList:
        """ Generate board diagram elements from a steno rule recursively. Propagate any background colors. """
        keys = rule.keys
        letters = rule.letters.strip()
        alt_text = rule.alt
        children = [item.child for item in rule]
        if letters and not any(map(str.isalpha, letters)):
            bg = self._bg.symbol if not any(map(str.isdigit, letters)) else self._bg.number
            if not alt_text:
                alt_text = letters
        if rule.is_linked:
            # A rule using linked strokes must follow this pattern: (.first)(~/~)(last.)
            strokes = [self._find_groups(child, show_letters, bg) for child in children]
            first, *middle, last = strokes
            chain_grp = self._factory.linked_group(first, last)
            grps = [elem for grp in middle for elem in grp]
            return [chain_grp, *grps]
        elif rule.is_inversion:
            # A rule using inversion connects the first two elements with arrows on top.
            grps = []
            for child in children:
                grps += self._find_groups(child, show_letters, bg)
            first, second = grps[:2]
            inv_grp = self._factory.inversion_group(first, second)
            return [*grps, inv_grp]
        elif rule.is_unmatched:
            return self._unmatched_key_groups(keys)
        elif rule.is_rare:
            bg = self._bg.rare
        elif rule.is_stroke:
            bg = self._bg.spelling
        elif rule.is_word:
            bg = self._bg.brief
        # A rule with one child using the same letters is usually an analysis. It should be unwrapped.
        if len(children) == 1:
            child = children[0]
            if letters == child.letters:
                return self._find_groups(child, show_letters, bg)
        # Try to find an existing key shape for this rule. If we find one, we're done.
        groups = self._rule_groups(keys, letters * show_letters, alt_text, bg)
        if groups:
            return groups
        # If there are children, add elements recursively from each one.
        if children:
            return [elem for child in children
                    for elem in self._find_groups(child, show_letters, bg)]
        # There may not be compound elements for everything; in that case, use elements for each raw key.
        return self._matched_key_groups(keys)

    def _make_svg(self, groups:GroupList, aspect_ratio:float=None):
        """ If no aspect ratio is given, a ratio of 0.0001 ensures that all boards end up in one column.
            Copy the list to to avoid possible cache corruption. """
        return self._factory.make_svg([*groups], aspect_ratio or 0.0001)

    def draw_keys(self, keys:str, aspect_ratio:float=None) -> BoardDiagram:
        """ Generate a board diagram from a steno key string arranged according to <aspect ratio>. """
        groups = self._matched_key_groups(keys)
        return self._make_svg(groups, aspect_ratio)

    def draw_rule(self, rule:StenoRule, aspect_ratio:float=None, *, show_letters=True) -> BoardDiagram:
        """ Generate a board diagram from a steno rule object arranged according to <aspect ratio>. """
        groups = self._find_groups(rule, show_letters)
        return self._make_svg(groups, aspect_ratio)


def build_board_engine(keymap:StenoKeyLayout, board_defs:StenoBoardDefinitions) -> BoardEngine:
    svg_factory = SVGElementFactory()
    key_sep = keymap.separator_key()
    key_special = keymap.special_key()
    key_procs = board_defs.keys
    key_procs[key_sep] = {"sep": "1"}
    rule_procs = board_defs.rules
    text_tf = TextTransformer(FONT_SIZE_PX, **board_defs.font)
    layout = GridLayoutEngine(**board_defs.bounds)
    factory = BoardFactory(svg_factory, key_procs, rule_procs,
                           board_defs.offsets, board_defs.shapes, board_defs.glyphs, text_tf, layout)
    bg = FillColors()
    factory.set_base(bg.base)
    return BoardEngine(keymap, key_special, bg, factory)
