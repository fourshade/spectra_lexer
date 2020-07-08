from spectra_lexer.board.factory import BoardFactory, BoardElementFactory
from spectra_lexer.board.rule import BoardRule
from spectra_lexer.board.tfrm import GridLayoutEngine
from spectra_lexer.resource.board import StenoBoardDefinitions
from spectra_lexer.resource.keys import StenoKeyLayout
from spectra_lexer.resource.rules import StenoRule

# Marker type for an SVG steno board diagram.
BoardDiagram = str


class BoardEngine:
    """ Returns steno board diagrams corresponding to key strings and/or steno rules. """

    def __init__(self, keymap:StenoKeyLayout, factory:BoardFactory) -> None:
        self._to_skeys = keymap.rtfcre_to_skeys  # Converts user RTFCRE steno strings to s-keys.
        self._factory = factory                  # Factory for complete SVG board diagrams.
        self._id_cache = {}                      # Cache for board rules by ID.

    def _to_board_rule(self, rule:StenoRule) -> BoardRule:
        """ Convert a normal rule to board format and cache it if it has an ID (analysis rules do not). """
        r_id = rule.id
        if r_id and r_id in self._id_cache:
            return self._id_cache[r_id]
        skeys = self._to_skeys(rule.keys)
        letters = rule.letters.strip()
        alt_text = rule.alt
        children = [self._to_board_rule(item.child) for item in rule]
        br = BoardRule(skeys, letters, alt_text, children)
        br.is_linked = rule.is_linked
        br.is_inversion = rule.is_inversion
        br.is_unmatched = rule.is_unmatched
        br.is_rare = rule.is_rare
        br.is_fingerspelling = rule.is_stroke
        br.is_brief = rule.is_word
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
