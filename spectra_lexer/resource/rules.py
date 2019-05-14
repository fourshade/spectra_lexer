import re
from typing import Dict, FrozenSet, List, NamedTuple, Sequence, Tuple

from spectra_lexer.types.codec import AbstractCodec, CSONDict


class RuleFlags(FrozenSet[str]):
    """ Immutable set of string flags that each indicate some property of a rule. """

    # These are the acceptable string values for flags, as read from JSON.
    SPECIAL = "SPEC"   # Special rule used internally (in other rules). Only referenced by name.
    STROKE = "STRK"    # Exact match for a single stroke, not part of one. Handled by exact dict lookup.
    WORD = "WORD"      # Exact match for a single word. These rules do not adversely affect lexer performance.
    RARE = "RARE"      # Rule applies to very few words and could specifically cause false positives.
    OPTIONAL = "OPT"   # Optional or redundant rule. May be informational; removal will cause little effect.
    INVERSION = "INV"  # Inversion of steno order. Child rule keys will be out of order with respect to the parent.
    UNMATCHED = "BAD"  # Incomplete lexer result. This rule contains all the unmatched keys and no letters.
    GENERATED = "GEN"  # Lexer generated rule. This is always the root unless there are special circumstances.


class StenoRule(NamedTuple):
    """ A general rule mapping a set of steno keys to a set of letters. All contents are recursively immutable.
        Includes flags, a description, and a submapping of rules that compose it. """

    keys: str         # Raw string of steno keys that make up the rule.
    letters: str      # Raw English text of the word.
    flags: RuleFlags  # Immutable set of strings describing flags that apply to the rule.
    desc: str         # Textual description of the rule.
    rulemap: tuple    # Immutable sequence of tuples mapping child rules to letter positions *in order*.

    def __str__(self) -> str:
        """ The standard string representation of a rule is just its mapping of keys to letters. """
        return f"{self.keys} → {self.letters or '<special>'}"

    def caption(self) -> str:
        """ Generate a plaintext caption for a rule based on its child rules and flags. """
        description = self.desc
        # Lexer-generated rules display only the description by itself.
        if RuleFlags.GENERATED in self.flags:
            return description
        # Base rules (i.e. leaf nodes) display their keys to the left of their descriptions.
        if not self.rulemap:
            return f"{self.keys}: {description}"
        # Derived rules (i.e. non-leaf nodes) show the complete mapping of keys to letters in their description.
        return f"{self}: {description}"


class RuleMapItem(NamedTuple):
    """ Immutable data structure specifying the parent attach positions for a rule. """
    rule: StenoRule
    start: int
    length: int


class _RawRule(NamedTuple):
    """ Data structure for raw string fields read from each line in a JSON rules file. """
    keys: str     # RTFCRE formatted series of steno strokes.
    pattern: str  # English text pattern, consisting of raw letters as well as references to other rules.
    flag_list: Sequence[str] = ()  # Optional sequence of flag strings.
    description: str = ""          # Optional description for when the rule is displayed in the GUI.


class RulesDictionary(dict, AbstractCodec):
    """ Class which takes a source dict of raw JSON rule entries with nested references and parses
        them recursively to get a final dict of independent steno rules indexed by internal name. """

    # Delimiter between letters and their rule alias in [] brackets.
    _ALIAS_DELIM = "|"
    # Available bracket pairs for parsing rules.
    _LEFT_BRACKETS = r'\(\['
    _RIGHT_BRACKETS = r'\)\]'
    # Rule substitutions must match:
    _SUBRULE_RX = re.compile(fr'[{_LEFT_BRACKETS}]'                      # a left bracket, 
                             fr'[^{_LEFT_BRACKETS}{_RIGHT_BRACKETS}]+?'  # one or more non-brackets, 
                             fr'[{_RIGHT_BRACKETS}]')                    # and a right bracket.

    _src_dict: Dict[str, list] = {}  # Keep the source dict in the instance to avoid passing it everywhere.
    inverse: Dict[StenoRule, str]    # An inverse dict is useful when converting back to JSON form.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._update_inverse()

    def _update_inverse(self):
        """ The inverse dict needs to be re-created to sync with any changes. """
        # TODO: Make the two dicts match after *any* update.
        self.inverse = {v: k for k, v in self.items()}

    @classmethod
    def decode(cls, *all_data:bytes, **kwargs):
        """ Decode a collection of commented JSON dicts and parse every entry using mutual recursion.
            This will parse entries in a semi-arbitrary order, so make sure not to redo any. """
        self = cls()
        self._src_dict = CSONDict.decode(*all_data, **kwargs)
        for k in self._src_dict:
            try:
                if k not in self:
                    self._parse(k)
            except KeyError as e:
                raise KeyError(f"Illegal reference descended from rule {k}") from e
        self._update_inverse()
        return self

    def _parse(self, k:str) -> None:
        """ Parse a raw source dictionary rule into a StenoRule object and store it. """
        raw = _RawRule(*self._src_dict[k])
        # We have to substitute in the effects of all child rules. These determine the final letters and rulemap.
        letters, built_map = self._substitute(raw.pattern)
        # The flags and built rulemap must be frozen before final inclusion in an immutable rule.
        flags = RuleFlags(raw.flag_list)
        rulemap = tuple(built_map)
        self[k] = StenoRule(raw.keys, letters, flags, raw.description, rulemap)

    def _substitute(self, pattern:str, ref_rx=_SUBRULE_RX, delim=_ALIAS_DELIM) -> Tuple[str, List[RuleMapItem]]:
        """
        From a rule's raw pattern string, find all the child rule references in brackets and make a map
        so the format code can break it down again if needed. For those in () brackets, we must substitute
        in the letters: (.d)e(.s) -> des. For [] brackets, the letters and reference are given separately.

        Only already-finished rules from the results dict can be directly substituted. Any rules that are
        not finished yet will still contain their own child rules in brackets. If we find one of these,
        we have to parse it first in a recursive manner. Circular references will crash the program.
        """
        built_map = []
        m = ref_rx.search(pattern)
        while m:
            # For every child rule, strip the parentheses to get the dict key (and the letters for [] rules).
            rule_str = m.group()
            rule_key = rule_str[1:-1]
            if rule_str[0] == '(':
                letters = None
            else:
                (letters, rule_key) = rule_key.split(delim, 1)
            # Look up the child rule and parse it if it hasn't been yet. Even if we aren't using its letters,
            # we still need to parse it at this stage so that the correct reference goes in the rulemap.
            if rule_key not in self:
                self._parse(rule_key)
            rule = self[rule_key]
            # Add the rule to the map and substitute in the letters if necessary.
            if not letters:
                letters = rule.letters
            built_map.append(RuleMapItem(rule, m.start(), len(letters)))
            pattern = pattern.replace(rule_str, letters)
            m = ref_rx.search(pattern)
        return pattern, built_map

    def encode(self, **kwargs) -> bytes:
        """ Generate a raw rules dict by substituting references in each rulemap for their letters, then encode it. """
        raw = CSONDict({k: self._inv_parse(r) for k, r in self.items()})
        return raw.encode(**kwargs)

    def _inv_parse(self, r:StenoRule) -> _RawRule:
        """ Convert a StenoRule object into a raw series of fields. """
        # The pattern must be deduced from the letters, the rulemap, and the reference dict.
        pattern = self._inv_substitute(r.letters, r.rulemap)
        # Put the flags into a list. The keys and description are copied verbatim.
        return _RawRule(r.keys, pattern, list(r.flags), r.desc)

    def _inv_substitute(self, letters:str, rulemap:Sequence[RuleMapItem]) -> str:
        """ For each mapped rule with a name reference, replace the mapped letters with the reference. """
        # Go from right to left to preserve indexing.
        for item in reversed(rulemap):
            # Some rules aren't named or are special. Don't show these in the pattern.
            name = self.inverse.get(item.rule)
            if not name:
                continue
            # Some rules take up no letters. Don't add these even if references exist.
            start = item.start
            end = start + item.length
            if start == end:
                continue
            # Replace the letters this rule takes up with a standard parenthesized reference.
            letters = letters[:start] + f"({name})" + letters[end:]
        return letters
