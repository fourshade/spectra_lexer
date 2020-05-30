from functools import lru_cache
from typing import Dict, List, Sequence

from .element import BoardElementFactory, BoardElementGroup
from .tfrm import GridLayoutEngine

# Marker type for an SVG steno board diagram.
BoardDiagram = str


class BoardRule:
    """ Contains all information about a steno rule required for board rendering. """

    # Acceptable string values for board element flags.
    is_inversion = False
    is_linked = False
    is_unmatched = False
    is_rare = False
    is_fingerspelling = False
    is_brief = False

    def __init__(self, skeys:str, letters:str, alt_text:str, children:Sequence['BoardRule']) -> None:
        self.skeys = skeys         # String of steno s-keys that make up the rule.
        self.letters = letters     # English text of the rule, if any.
        self.alt_text = alt_text   # Alternate text to display when not in letters mode (or if there are no letters).
        self.children = children   # Sequence of child rules *in order*.


class BoardFactory:
    """ Builds steno board diagrams from rules in the given dictionaries.
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

    def __init__(self, elem_factory:BoardElementFactory, layout:GridLayoutEngine, special_key:str,
                 key_procs:Dict[str, List[str]], rule_procs:Dict[str, List[str]]) -> None:
        self._elem_factory = elem_factory  # Factory for board element groups.
        self._layout = layout              # Layout for multi-stroke diagrams.
        self._special_key = special_key    # Key combined with others without contributing to text.
        self._key_procs = key_procs        # Procedures for constructing and positioning single keys.
        self._rule_procs = rule_procs      # Procedures for constructing and positioning key combos.
        # Generate an XML element for a board diagram base with all keys.
        base_groups = [elem_factory.processed_group(procs[:-1], self.FILL_BASE)
                       for procs in key_procs.values()]
        self._base = elem_factory.collapse(*base_groups)

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
        star = self._special_key
        if procs is None and star in skeys and star != skeys:
            # Rules using the star should have that key separate from their text.
            leftover = skeys.replace(star, "")
            bg = self.FILL_COMBO
            elems += self._elems_from_skeys(star, bg)
            procs = self._rule_procs.get(leftover)
        if procs is not None:
            if letters:
                return [*elems, self._elem_factory.processed_group(procs, bg or self.FILL_RULE, letters)]
            elif alt_text:
                return [*elems, self._elem_factory.processed_group(procs, bg or self.FILL_ALT, alt_text)]
        return []

    def _elems_from_linked(self, rule:BoardRule, show_letters:bool, bg:str=None) -> List[BoardElementGroup]:
        """ A rule using linked strokes must follow this pattern: (.first)(~/~)(last.) """
        strokes = [self._elems_from_rule(child, show_letters, bg) for child in rule.children]
        return [self._elem_factory.linked_group(strokes[0], strokes[-1])]

    def _elems_from_inversion(self, rule:BoardRule, show_letters:bool, bg:str=None) -> List[BoardElementGroup]:
        """ A rule using inversion connects the first two elements with arrows. """
        grps = []
        for child in rule.children:
            grps += self._elems_from_rule(child, show_letters, bg)
        return [self._elem_factory.inversion_group(grps)]

    def _elems_from_rule(self, rule:BoardRule, show_letters:bool, bg:str=None) -> List[BoardElementGroup]:
        """ Generate board diagram elements from a steno rule recursively. Propagate any background colors. """
        skeys = rule.skeys
        letters = rule.letters
        alt_text = rule.alt_text
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
        elif rule.is_fingerspelling:
            bg = self.FILL_SPELLING
        elif rule.is_brief:
            bg = self.FILL_BRIEF
        elems = self._elems_from_rule_info(skeys, letters if show_letters else "", alt_text, bg)
        if elems:
            return elems
        elif rule.children:
            # Add elements recursively from all child rules.
            return [elem for child in rule.children for elem in self._elems_from_rule(child, show_letters, bg)]
        # There may not be compound elements for everything; in that case, use elements for each raw key.
        return self._elems_from_skeys(skeys)

    def _make_svg(self, elems:Sequence[BoardElementGroup], aspect_ratio:float=None) -> BoardDiagram:
        return self._elem_factory.make_svg(self._base, elems, self._layout, aspect_ratio)

    def draw_keys(self, skeys:str, aspect_ratio:float=None) -> BoardDiagram:
        """ Generate a board diagram from a key string arranged according to <aspect ratio>.
            Copy the element list to avoid corrupting the caches. """
        elems = self._elems_from_skeys(skeys)[:]
        return self._make_svg(elems, aspect_ratio)

    def draw_rule(self, rule:BoardRule, aspect_ratio:float=None, *, show_letters=True) -> BoardDiagram:
        """ Generate a board diagram from a rule object arranged according to <aspect ratio>.
            Copy the element list to avoid corrupting the caches. """
        elems = self._elems_from_rule(rule, show_letters)[:]
        return self._make_svg(elems, aspect_ratio)
