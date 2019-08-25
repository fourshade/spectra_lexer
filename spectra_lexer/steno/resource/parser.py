from collections import defaultdict
import re
from typing import Dict, Iterable, Tuple

from .rules import RuleFlags, RuleMapItem, StenoRule


class RuleParser:
    """ Class which takes a source dict of raw JSON rule entries with nested references and parses
        them recursively to get a final dict of independent steno rules indexed by internal name. """

    # Delimiter between letters and their rule alias in [] brackets.
    _ALIAS_DELIM = "|"
    # Rule substitutions must match:
    _SUBRULE_RX = re.compile(r'[([]'        # a left bracket,
                             r'[^()[\]]+?'  # one or more non-brackets,
                             r'[)\]]')      # and a right bracket.

    _rules: Dict[str, StenoRule] = {}  # Main rule dict, kept in order to parse rules back into JSON.
    _raw_dict: Dict[str, list] = {}    # Raw source dict, kept in the instance to avoid passing it everywhere.

    def parse(self, *dicts:Dict[str, list]) -> Dict[str, StenoRule]:
        """ Parse every entry from one or more raw JSON-decoded rule dicts using mutual recursion.
            This will parse entries in a semi-arbitrary order, so make sure not to redo any. """
        rules = self._rules = {}
        raw_dict = self._raw_dict = {}
        for d in dicts:
            conflicts = d.keys() & raw_dict.keys()
            if conflicts:
                raise ValueError(f"Found rule keys appearing more than once: {conflicts}")
            raw_dict.update(d)
        for k in raw_dict:
            try:
                if k not in rules:
                    self._parse(k)
            except KeyError as e:
                raise KeyError(f"Illegal reference descended from rule {k}") from e
            except RecursionError as e:
                raise RecursionError(f"Circular reference descended from rule {k}") from e
        return rules

    def _parse(self, k:str, flags=RuleFlags(), desc="") -> None:
        """ Parse a raw source dictionary rule into a StenoRule object and store it. The raw fields are:
            keys:    RTFCRE formatted string of steno strokes.
            pattern: English text pattern string, consisting of raw letters as well as references to other rules.
            flags:   Optional list of flag strings. Must be frozen before final inclusion in an immutable rule.
            desc:    Optional description for when the rule is displayed in the GUI. """
        keys, pattern, *optional = self._raw_dict[k]
        if optional:
            if len(optional) > 1:
                desc = optional.pop()
            flags = RuleFlags(optional.pop())
        # We have to substitute in the effects of all child rules found in the pattern.
        # These determine the final letters and rulemap. The keys and description strings are fine as-is.
        letters, rulemap = self._substitute(pattern)
        self._rules[k] = StenoRule(keys, letters, flags, desc, rulemap)

    def _substitute(self, pattern:str) -> Tuple[str, Tuple[RuleMapItem]]:
        """
        From a rule's raw pattern string, find all the child rule references in brackets and make a map
        so the format code can break it down again if needed. For those in () brackets, we must substitute
        in the letters: (.d)e(.s) -> des. For [] brackets, the letters and reference are given separately.

        Only already-finished rules from the results dict can be directly substituted. Any rules that are
        not finished yet will still contain their own child rules in brackets. If we find one of these,
        we have to parse it first in a recursive manner. Circular references are not allowed.
        """
        built_map = []
        # Go from right to left to preserve indexing (this requires making the RX iterator into a list).
        matches = [*self._SUBRULE_RX.finditer(pattern)]
        for m in matches[::-1]:
            # For every match, strip the parentheses to get the dict key (and the letters for [] rules).
            match_str = m.group()
            reference = match_str[1:-1]
            if match_str[0] == '(':
                letters = None
                k = reference
            else:
                letters, k = reference.split(self._ALIAS_DELIM, 1)
            # Look up the child rule and parse it if it hasn't been yet. Even if we aren't using its letters,
            # we still need to parse it at this stage so that the correct reference goes in the rulemap.
            if k not in self._rules:
                self._parse(k)
            rule = self._rules[k]
            # Add the rule to the map and substitute in the letters if necessary.
            if letters is None:
                letters = rule.letters
            built_map.append(RuleMapItem(rule, m.start(), len(letters)))
            pattern = pattern.replace(match_str, letters)
        # The built rulemap must be frozen into a tuple for immutability.
        return pattern, (*built_map,)

    def compile_to_raw(self, results:Iterable[StenoRule]) -> Dict[str, list]:
        """ Parse steno rules back into raw list form suitable for JSON encoding by substituting each
            child rule in its rulemap for its letters and auto-generating rule names. """
        # Invert the main dict in order to map rules back to names.
        inverse = defaultdict(str, {v: k for k, v in self._rules.items()})
        # Start with a copy of the original raw rules so that references don't break.
        raw_rules = self._raw_dict.copy()
        for r in results:
            # Convert the letter string into a list to allow in-place modification.
            letters = [*r.letters]
            # Replace each mapped rule with a name reference. Go from right to left to preserve indexing.
            for rule, start, length in r.rulemap[::-1]:
                name = inverse[rule]
                if name:
                    # Replace the letters this rule takes up with its parenthesized reference name.
                    end = start + length
                    letters[start:end] = "(", name, ")"
            # Rejoin the letters and put the flags into a list. The keys and description are copied verbatim.
            word = "".join(letters)
            flags = [*r.flags]
            raw_rules[str(r)] = [r.keys, word, flags, r.desc]
        return raw_rules
