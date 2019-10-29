from typing import Dict, Iterator, List, Optional, Tuple


class RuleMapItem:
    """ Immutable data structure specifying a child rule with the positions where it attaches to its parent. """

    def __init__(self, name:str, start:int, length:int) -> None:
        self.name = name      # Child rule name.
        self.start = start    # Index of the first character on the parent (letterwise) that the rule describes.
        self.length = length  # Length of the span of characters on the parent that the rule describes.


class StenoRule:
    """ A general rule mapping a set of steno keys to a set of letters. All contents are recursively immutable. """

    def __init__(self, name:str, keys:str, letters:str, flags=frozenset(), caption="", rulemap=()) -> None:
        self.name = name        # Rule name string. Used as a unique identifier.
        self.keys = keys        # Raw string of steno keys that make up the rule.
        self.letters = letters  # Raw English text of the word.
        self.flags = flags      # Immutable set of string flags that apply to the rule.
        self.caption = caption  # Textual description of the rule.
        self.rulemap = rulemap  # Immutable sequence of tuples mapping child rules to letter positions *in order*.

    def __str__(self) -> str:
        """ The standard string representation of a rule is its caption. """
        return self.caption


class RuleParser:
    """ Converts steno rules from JSON arrays to StenoRule objects. """

    def __init__(self, raw_rules:Dict[str, list], ref_delims="()", alias_delim="|") -> None:
        self._raw_rules = raw_rules      # Dict of raw steno rules in list form from JSON.
        self._ref_delims = ref_delims    # Delimiters marking the start and end of a rule reference.
        self._alias_delim = alias_delim  # Delimiter between letters and their rule alias when different.
        self._rules = {}                 # Dict of finished steno rules indexed by an internal reference name.

    def __iter__(self) -> Iterator[StenoRule]:
        """ Yield all finished rules, parsing missing ones as necessary. """
        return map(self._parse, self._raw_rules)

    def _parse(self, k:str) -> Optional[StenoRule]:
        """ Recursively parse a rule from raw list form into a StenoRule object. The fields (in order) are:
            keys:    RTFCRE formatted string of steno strokes.
            pattern: English text pattern string, consisting of raw letters as well as references to other rules.
            flags:   Optional sequence of flag strings.
            desc:    Optional description for when the rule is displayed in the GUI. """
        # Look up a rule. If it is missing but we have a raw version, parse it, otherwise return None.
        if k in self._rules:
            return self._rules[k]
        if k not in self._raw_rules:
            return None
        raw_rule = self._raw_rules[k]
        try:
            keys, pattern, *optional = raw_rule
        except ValueError:
            raise ValueError(f"Not enough fields for rule {k}")
        flags = optional.pop(0) if optional else ()
        desc = optional.pop(0) if optional else "No description"
        if optional:
            raise ValueError(f"Too many fields for rule {k}: extra = {optional}")
        # The pattern must be always parsed into letters and a rulemap.
        try:
            letters, rulemap = self._substitute(pattern)
        except ValueError as e:
            raise ValueError(f"Unmatched brackets in rule {k}") from e
        except RecursionError as e:
            raise RecursionError(f"Circular reference descended from rule {k}") from e
        # The flags and rulemap must be frozen for immutability.
        flags = frozenset(flags)
        rulemap = tuple(rulemap)
        # Generate a plaintext caption to finish.
        if rulemap and letters:
            # Derived rules show the complete mapping of keys to letters in their caption.
            caption = f"{keys} → {letters}: {desc}"
        else:
            # Base rules display only their keys to the left of their descriptions.
            caption = f"{keys}: {desc}"
        rule = self._rules[k] = StenoRule(k, keys, letters, flags, caption, rulemap)
        return rule

    def _substitute(self, pattern:str) -> Tuple[str, List[RuleMapItem]]:
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
        lb, rb = self._ref_delims
        while lb in p_list:
            # Rule substitutions must match a left bracket and a right bracket.
            start = index(lb)
            end = index(rb) + 1
            # For every match, strip the parentheses to get the dict key (and the letters for aliased rules).
            reference = "".join(p_list[start+1:end-1])
            *alias, k = reference.split(self._alias_delim, 1)
            # Look up the child rule reference (and parse it if it hasn't been yet).
            rule = self._parse(k)
            if rule is None:
                raise KeyError(f"Illegal rule reference {k} in pattern {pattern}")
            letters = alias[0] if alias else rule.letters
            # Add the rule to the map and substitute the letters into the pattern.
            rulemap.append(RuleMapItem(k, start, len(letters)))
            p_list[start:end] = letters
        return "".join(p_list), rulemap


class InverseRuleParser:
    """ Converts lexer rule maps into rule-compatible JSON arrays. """

    def __init__(self, ref_delims="()") -> None:
        self._ref_delims = ref_delims  # Delimiters marking the start and end of a rule reference.
        self._raw_rules = {}           # Dict of raw steno rules in list form for JSON.
        self._count = 0

    def add(self, keys:str, letters:str, rulemap:List[Tuple[str, int, int]]) -> None:
        """ Parse a translation and rule map into raw list form suitable for JSON encoding by substituting each
            child rule for its letters and using serial numbers as rule names. """
        lb, rb = self._ref_delims
        # Convert the letter string into a list to allow in-place modification.
        letters = [*letters]
        # Replace each rule's letters with a parenthesized name reference. Go from right to left to preserve indexing.
        for name, start, length in rulemap[::-1]:
            end = start + length
            letters[start:end] = lb, name, rb
        word = "".join(letters)
        self._raw_rules[str(self._count)] = [keys, word]
        self._count += 1

    def to_dict(self) -> Dict[str, list]:
        return self._raw_rules
