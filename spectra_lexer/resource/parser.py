import re
from typing import Dict, Iterable, List, NamedTuple, Sequence, Tuple

from .rules import RuleFlags, RuleMapItem, StenoRule


class _RawRule(NamedTuple):
    """ Data structure for raw string fields read from each line in a JSON rules file. """
    keys: str     # RTFCRE formatted series of steno strokes.
    pattern: str  # English text pattern, consisting of raw letters as well as references to other rules.
    flag_list: Sequence[str] = ()  # Optional sequence of flag strings.
    description: str = ""          # Optional description for when the rule is displayed in the GUI.


class RuleParser(dict):
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

    _src_dict: Dict[str, list]      # Keep the raw source dict in the instance to avoid passing it everywhere.
    _inverse: Dict[StenoRule, str]  # An inverse dict is useful when converting back to JSON form.

    def __init__(self, src_dict:Dict[str, list]):
        """ Parse and add every entry from a raw JSON-decoded dict using mutual recursion.
            This will parse entries in a semi-arbitrary order, so make sure not to redo any. """
        super().__init__()
        self._src_dict = src_dict
        for k in src_dict:
            try:
                if k not in self:
                    self._parse(k)
            except KeyError as e:
                raise KeyError(f"Illegal reference descended from rule {k}") from e
        self._inverse = {v: k for k, v in self.items()}

    def _parse(self, k:str) -> None:
        """ Parse a raw source dictionary rule into a StenoRule object and store it. """
        raw = _RawRule(*self._src_dict[k])
        # We have to substitute in the effects of all child rules. These determine the final letters and rulemap.
        letters, built_map = self._substitute(raw.pattern)
        # The flags and built rulemap must be frozen before final inclusion in an immutable rule.
        flags = RuleFlags(raw.flag_list)
        rulemap = (*built_map,)
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
                letters, rule_key = rule_key.split(delim, 1)
            # Look up the child rule and parse it if it hasn't been yet. Even if we aren't using its letters,
            # we still need to parse it at this stage so that the correct reference goes in the rulemap.
            if rule_key not in self:
                self._parse(rule_key)
            rule = self[rule_key]
            # Add the rule to the map and substitute in the letters if necessary.
            if letters is None:
                letters = rule.letters
            built_map.append(RuleMapItem(rule, m.start(), len(letters)))
            pattern = pattern.replace(rule_str, letters)
            m = ref_rx.search(pattern)
        return pattern, built_map

    def compile_to_raw(self, results:Iterable[StenoRule]) -> Dict[str, list]:
        """ Parse steno rules back into raw form suitable for JSON encoding by substituting each
            child rule in its rulemap for its letters and auto-generating rule names if necessary.
            Also include our original raw rules so the references don't break. """
        new_rules = {str(r): self._inv_parse(r) for r in results}
        new_rules.update(self._src_dict)
        return new_rules

    def _inv_parse(self, r:StenoRule) -> list:
        """ Convert a StenoRule object into a raw list of fields for JSON. """
        # The pattern must be deduced from the letters, the rulemap, and the reference dict.
        pattern = self._inv_substitute(r.letters, r.rulemap)
        # Put the flags into a list. The keys and description are copied verbatim.
        return [r.keys, pattern, [*r.flags], r.desc]

    def _inv_substitute(self, letters:str, rulemap:Sequence[RuleMapItem]) -> str:
        """ For each mapped rule with a name reference, replace the mapped letters with the reference. """
        # Go from right to left to preserve indexing.
        for item in reversed(rulemap):
            # Some rules aren't named or are special. Don't show these in the pattern.
            name = self._inverse.get(item.rule)
            if not name:
                continue
            # Some rules take up no letters. Don't add these even if references exist.
            length = item.length
            if not length:
                continue
            # Replace the letters this rule takes up with a standard parenthesized reference.
            start = item.start
            end = start + length
            letters = f"{letters[:start]}({name}){letters[end:]}"
        return letters
