""" Module for generating steno board diagram elements. """

from math import ceil
from typing import Callable, Dict, Iterable, List, Sequence, Tuple

from .elements import XMLElementDict
from .path import SVGPathInversion
from .svg import SVGDocument, SVGElement, SVGGroup
from spectra_lexer.resource import RuleFlags, StenoRule


class KeyMatcher:
    """ Matches elements to keys in dicts. """

    _convert_to_skeys: Callable[[str], str]  # Conversion function from RTFCRE to s-keys.
    _dicts: List[Dict[str, SVGElement]]      # Dicts with elements for each key when it is normal/unmatched.

    def __init__(self, to_skeys:Callable[[str], str],
                 key_dict:Dict[str, SVGElement], unmatched_dict:Dict[str, SVGElement]):
        self._convert_to_skeys = to_skeys
        self._dicts = [key_dict, unmatched_dict]

    def __call__(self, keys:str, unmatched:bool=False) -> List[SVGElement]:
        """ Return a board diagram element for each raw key. Display question marks for unmatched keys. """
        d = self._dicts[unmatched]
        return [d[k] for k in self._convert_to_skeys(keys)]


class RuleMatcher:
    """ Generates lists of elements for stroke diagrams, each of which contains a basic background
        and a number of discrete graphical elements matched to raw keys and/or simple rules. """

    _key_matcher: KeyMatcher
    _rule_to_element: Dict[StenoRule, SVGElement]

    def __init__(self, key_matcher:KeyMatcher, rules:Dict[str, StenoRule], elements:Dict[str, SVGElement]):
        self._key_matcher = key_matcher
        self._rule_to_element = {rules[k]: elements[k] for k in elements if k in rules}

    def __call__(self, rule:StenoRule) -> List[SVGElement]:
        """ Yield board diagram elements from a steno rule recursively. """
        elem = self._rule_to_element.get(rule)
        # If the rule itself has an entry in the dict, yield that element and we're done.
        if elem is not None:
            return [elem]
        rulemap = rule.rulemap
        if not rulemap:
            # If the rule has no children and no dict entry, just yield elements for each raw key.
            unmatched = RuleFlags.UNMATCHED in rule.flags
            return self._key_matcher(rule.keys, unmatched)
        # If a rule has children, yield their composition.
        elems = []
        for item in rulemap:
            elems += self(item.rule)
        # Rules using inversions may be drawn with arrows.
        if RuleFlags.INVERSION in rule.flags:
            elems.append(SVGPathInversion(*elems))
        return elems


class BoardEncoder:
    """ Generates the final board data with transforms fitted to the bounds of the display widget. """

    _bounds: Sequence[int]  # (x, y, w, h) sequence of coordinates for the viewbox on one stroke diagram.

    def __init__(self, bounds:Sequence[int]):
        self._bounds = bounds

    def __call__(self, groups:Sequence[SVGGroup], ratio:float) -> bytes:
        """ Transform each SVG group and encode the entire document. """
        rows, cols = self._grid_dimensions(len(groups), ratio)
        x, y, w, h = self._bounds
        for i, group, in enumerate(groups):
            # Subdiagrams are tiled left-to-right, top-to-bottom in a grid layout.
            step_y, step_x = divmod(i, cols)
            group.transform(1, 1, w * step_x, h * step_y)
        document = SVGDocument(groups)
        document.set_viewbox(x, y, w * cols, h * rows)
        return document.encode()

    def _grid_dimensions(self, count:int, full_ratio:float) -> Tuple[int, int]:
        """ Calculate the best arrangement of <count> sub-diagrams in rows and columns for the best possible scale.
            <board_ratio> is the aspect ratio of one diagram; <full_ratio> is that of the full viewing area. """
        _, _, w, h = self._bounds
        board_ratio = w / h
        short_ratio, long_ratio = sorted([board_ratio, full_ratio])
        rel_ratio = count * short_ratio / long_ratio
        short_bound = int(rel_ratio ** 0.5) or 1
        # Find the two possibilities for optimum arrangement and choose the one with the larger scale.
        tries = short_bound, short_bound + 1
        sl_pairs = [(s, ceil(count / s)) for s in tries]
        short_dim, long_dim = max(sl_pairs, key=lambda pair: min(short_ratio / pair[0], long_ratio / pair[1]))
        if (board_ratio < full_ratio):
            return short_dim, long_dim
        else:
            return long_dim, short_dim


class ElementGrouper:

    _bases: Sequence[SVGElement]  # Base elements of the diagram, positioned first in every stroke.
    _sentinel: object             # Sentinel object to indicate a new stroke.

    def __init__(self, bases:Sequence[SVGElement], sentinel:object):
        self._bases = bases
        self._sentinel = sentinel

    def __call__(self, elems:Iterable[SVGElement]) -> List[SVGGroup]:
        """ Arrange all elements into a list for each stroke based on sentinels.
            Each new group starts with the base elements. """
        current = SVGGroup(self._bases)
        groups = [current]
        for elem in elems:
            if elem is self._sentinel:
                current = SVGGroup(self._bases)
                groups.append(current)
            else:
                current.append(elem)
        return groups


class BoardGenerator:

    _key_matcher: KeyMatcher
    _rule_matcher: RuleMatcher
    _grouper: ElementGrouper
    _encoder: BoardEncoder

    def __init__(self, xml_dict:XMLElementDict, bounds:Sequence[int],
                 to_skeys:Callable[[str], str], sep:str, rules:Dict[str, StenoRule]):
        base_dict = xml_dict["base"]
        key_dict = xml_dict["key"]
        unmatched_dict = xml_dict["qkey"]
        rule_dict = xml_dict["rule"]
        # Create a sentinel element as a stroke delimiter.
        bases = list(base_dict.values())
        sentinel = key_dict[sep] = unmatched_dict[sep] = SVGElement()
        self._key_matcher = KeyMatcher(to_skeys, key_dict, unmatched_dict)
        self._rule_matcher = RuleMatcher(self._key_matcher, rules, rule_dict)
        self._grouper = ElementGrouper(bases, sentinel)
        self._encoder = BoardEncoder(bounds)

    def from_keys(self, keys:str, ratio:float) -> bytes:
        elems = self._key_matcher(keys)
        return self._generate(elems, ratio)

    def from_rule(self, rule:StenoRule, ratio:float) -> bytes:
        elems = self._rule_matcher(rule)
        return self._generate(elems, ratio)

    def _generate(self, elems:Iterable[SVGElement], ratio:float) -> bytes:
        groups = self._grouper(elems)
        return self._encoder(groups, ratio)
