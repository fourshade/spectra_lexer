from collections import defaultdict
from typing import Dict, Iterable, Tuple

from .rules import RuleFlags, RuleMapItem, StenoRule


class RuleParser:
    """ Class which takes a source dict of raw JSON rule entries with nested references and parses
        them recursively to get a final dict of independent steno rules indexed by internal name. """

    # Delimiters marking the start and end of a rule reference.
    _SUB_DELIMS = "()"
    # Delimiter between letters and their rule alias when different.
    _ALIAS_DELIM = "|"

    _rules: Dict[str, StenoRule] = {}  # Main rule dict, kept in order to parse rules back into JSON.
    _raw_dict: Dict[str, list] = None  # Raw source dict, kept in the instance to avoid passing it everywhere.

    def parse(self, *dicts:Dict[str, list]) -> Dict[str, StenoRule]:
        """ Clear any previous results, then load every entry from one or more raw JSON-decoded rule dicts.
            Return a dict containing each rule after parsing. """
        self._rules = {}
        raw_dict = self._raw_dict = {}
        for d in dicts:
            # Check for key conflicts between this dict and previous ones before merging.
            conflicts = d.keys() & raw_dict.keys()
            if conflicts:
                raise ValueError(f"Found rule keys appearing more than once: {conflicts}")
            raw_dict.update(d)
        return {k: self[k] for k in raw_dict}

    def __getitem__(self, k:str) -> StenoRule:
        """ Attempt to find a rule by the given key in the main dict. If not found, check the raw source dictionary.
            If one is found there, parse that into a StenoRule object and store it. The raw fields are:
            keys:    RTFCRE formatted string of steno strokes.
            pattern: English text pattern string, consisting of raw letters as well as references to other rules.
            flags:   Optional sequence of flag strings.
            desc:    Optional description for when the rule is displayed in the GUI. """
        if k in self._rules:
            return self._rules[k]
        try:
            keys, pattern, *optional = self._raw_dict[k]
        except KeyError as e:
            raise KeyError(f"Illegal rule reference: {k}") from e
        except ValueError as e:
            raise ValueError(f"Not enough parameters for rule {k}") from e
        flags = optional.pop(0) if optional else ()
        desc = optional.pop(0) if optional else ""
        if optional:
            raise ValueError(f"Too many parameters for rule {k}: extra = {optional}")
        # The pattern must be always parsed into letters and a rulemap.
        try:
            letters, rulemap = self._substitute(pattern)
        except ValueError as e:
            raise RecursionError(f"Unmatched brackets in rule {k}") from e
        except RecursionError as e:
            raise RecursionError(f"Circular reference descended from rule {k}") from e
        # The flags and rulemap must be frozen for immutability. The keys and description strings are fine as-is.
        rule = self._rules[k] = StenoRule(keys, letters, RuleFlags(flags), desc, (*rulemap,))
        return rule

    def _substitute(self, pattern:str) -> Tuple[str, list]:
        """
        From a rule's raw pattern string, find all the child rule references in () brackets and make a map
        so the formatting code can properly render the relationships between rules and where they occur.
        If no | is included, substitute in the letters and keep the references:

            (.d)e(.s) -> letters = 'des', map = [.d at 0, .s at 2]

        If a | is included, the letters and reference are given separately:

            (q.)(u|w.) -> letters = 'qu', map = [q. at 0, w. at 1]

        Only already-finished rules from the main rule dict can be directly substituted.
        Any rules that are not finished yet will still contain their own child rules (if any) in brackets.
        In the example above, the rules q. and w. must be parsed before we can finish the 'qu' rule.
        Those particular rules have no further child references, but we don't know that until we parse them.
        This happens in a recursive manner. Circular references are not allowed (and would not make sense anyway).
        """
        rulemap = []
        # Convert the pattern string into a list to allow in-place modification.
        p_list = [*pattern]
        index = p_list.index
        lb, rb = self._SUB_DELIMS
        while lb in p_list:
            # Rule substitutions must match a left bracket and a right bracket.
            start = index(lb)
            end = index(rb) + 1
            # For every match, strip the parentheses to get the dict key (and the letters for aliased rules).
            reference = "".join(p_list[start+1:end-1])
            *alias, k = reference.split(self._ALIAS_DELIM, 1)
            # Look up the child rule reference (and parse it if it hasn't been yet).
            rule = self[k]
            letters = alias[0] if alias else rule.letters
            # Add the rule to the map and substitute the letters into the pattern.
            rulemap.append(RuleMapItem(rule, start, len(letters)))
            p_list[start:end] = letters
        return "".join(p_list), rulemap

    def compile_to_raw(self, results:Iterable[StenoRule]) -> Dict[str, list]:
        """ Parse steno rules back into raw list form suitable for JSON encoding by substituting each
            child rule in its rulemap for its letters and auto-generating rule names. """
        # Invert the main dict in order to map rules back to names.
        inverse = defaultdict(str, {v: k for k, v in self._rules.items()})
        raw_rules = {}
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
