from collections import defaultdict, namedtuple
from typing import Dict, Iterable, Tuple


class RuleFlags(frozenset):
    """ Immutable set of string flags that each indicate some property of a rule. """

    class Flag(str):
        """ A flag string constant with shortcuts on attribute access. """
        def __get__(self, instance:frozenset, owner:type=None):
            """ If a flag constant is accessed on a class, return a new instance containing it. """
            if instance is None:
                return owner([self])
            # If a flag constant is accessed on an instance, test for membership.
            return self in instance

    # These are the acceptable string values for flags, as read from JSON.
    special = Flag("SPEC")   # Special rule used internally (in other rules). Only referenced by name.
    stroke = Flag("STRK")    # Exact match for a single stroke, not part of one. Handled by exact dict lookup.
    word = Flag("WORD")      # Exact match for a single word. These rules do not adversely affect lexer performance.
    rare = Flag("RARE")      # Rule applies to very few words and could specifically cause false positives.
    optional = Flag("OPT")   # Optional or redundant rule. May be informational; removal will cause little effect.
    inversion = Flag("INV")  # Inversion of steno order. Child rule keys will be out of order with respect to parent.
    linked = Flag("LINK")    # Rule that uses keys from two strokes. This complicates stroke delimiting.
    unmatched = Flag("BAD")  # Incomplete lexer result. This rule contains all the unmatched keys and no letters.
    generated = Flag("GEN")  # Lexer generated rule. This is always the root unless there are special circumstances.


class StenoRule(namedtuple("StenoRule", "keys letters flags desc rulemap")):
    """ A general rule mapping a set of steno keys to a set of letters. All contents are recursively immutable.
        keys: str        - Raw string of steno keys that make up the rule.
        letters: str     - Raw English text of the word.
        flags: RuleFlags - Immutable set of strings describing flags that apply to the rule.
        desc: str        - Textual description of the rule.
        rulemap: tuple   - Immutable sequence of tuples mapping child rules to letter positions *in order*."""

    def __str__(self) -> str:
        """ The standard string representation of a rule is just its mapping of keys to letters. """
        return f"{self.keys} → {self.letters or '<special>'}"

    def caption(self) -> str:
        """ Generate a plaintext caption for a rule based on its child rules and flags. """
        description = self.desc
        # Lexer-generated rules display only the description by itself.
        if self.flags.generated:
            return description
        # Base rules (i.e. leaf nodes) display their keys to the left of their descriptions.
        if not self.rulemap:
            return f"{self.keys}: {description}"
        # Derived rules (i.e. non-leaf nodes) show the complete mapping of keys to letters in their description.
        return f"{self}: {description}"

    @classmethod
    def special(cls, keys:str, desc:str, flags=RuleFlags()):
        """ Make a special (no-letter) rule. """
        return cls(keys, "", flags, desc, ())

    @classmethod
    def generated(cls, keys:str, letters:str, rulemap:list, desc="Found complete match.", flags=RuleFlags.generated):
        """ Make a new lexer-generated rule with the correct caption, flags, and frozen rulemap. """
        return cls(keys, letters, flags, desc, (*rulemap,))

    @classmethod
    def unmatched(cls, keys:str, letters:str, rulemap:list, unmatched:str, flags=RuleFlags.unmatched):
        """ The output is nowhere near reliable if some keys couldn't be matched.
            Add a child rule with unmatched keys to the rulemap, then generate and return the parent rule. """
        if rulemap:
            last_match_end = rulemap[-1].start + rulemap[-1].length
            desc = "Incomplete match. Not reliable."
        else:
            last_match_end = 0
            desc = "No matches found."
        unmatched_span = len(letters) - last_match_end
        child_rule = cls(unmatched, "", flags, "unmatched keys", ())
        rulemap.append(RuleMapItem(child_rule, last_match_end, unmatched_span))
        return cls.generated(keys, letters, rulemap, desc)


class RuleMapItem(namedtuple("RuleMapItem", "rule start length")):
    """ Immutable data structure specifying a child rule with the positions where it attaches to its parent.
        rule: StenoRule - Child rule object.
        start: int      - Index of the first character on the parent (letterwise) that the rule describes.
        length: int     - Length of the span of characters on the parent that the rule describes. """


class RulesDictionary(Dict[str, StenoRule]):
    """ Dictionary of steno rules indexed by an internal reference name. """

    _SUB_DELIMS = "()"  # Delimiters marking the start and end of a rule reference.
    _ALIAS_DELIM = "|"  # Delimiter between letters and their rule alias when different.

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._raw_dict = {}  # Raw source dict, kept in the instance to avoid passing it everywhere.

    def update_from_raw(self, raw_dict:Dict[str, list]) -> None:
        """ Take a source dict of raw JSON rule entries with nested references and parse them recursively. """
        self._raw_dict.update(raw_dict)
        for k in raw_dict:
            if k not in self:
                self._parse(k)

    def _parse(self, k:str) -> None:
        """ Parse a rule from the raw source dictionary into a StenoRule object and store it. The raw fields are:
            keys:    RTFCRE formatted string of steno strokes.
            pattern: English text pattern string, consisting of raw letters as well as references to other rules.
            flags:   Optional sequence of flag strings.
            desc:    Optional description for when the rule is displayed in the GUI. """
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
        self[k] = StenoRule(keys, letters, RuleFlags(flags), desc, (*rulemap,))

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
            if k not in self:
                self._parse(k)
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
        inverse = defaultdict(str, {v: k for k, v in self.items()})
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
