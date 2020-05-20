from collections import Counter
from typing import AbstractSet, Iterator, List

from .sub import TextSubstitutionParser


class StenoRule:
    """ A general rule mapping a set of steno keys to a set of letters. There are two major types:
        Simple/base - a fundamental rule mapping a set of keys to letters. These may be used alone.
        Compound/derived - a more complex rule composed of simple or even other compound rules recursively.
        For compound rules, every key in the parent should be used by exactly one child. """

    class Connection:
        """ Contains a child rule and where it fits within the parent. """
        def __init__(self, child:"StenoRule", start:int, length:int) -> None:
            self.child = child    # Child rule object.
            self.start = start    # Index of the first letter in the parent where the child attaches.
            self.length = length  # Number of letters that the child spans in the parent.

    class Flag(str):
        """ A flag string constant with shortcuts on attribute access. """
        def __get__(self, instance:"StenoRule", owner:type=None):
            """ If a flag is accessed as an instance attribute, test for membership.
                If accessed as a class attribute, return its value. """
            if instance is None:
                return self
            return self in instance._flags

    # Acceptable string values for lexer flags, as read from JSON.
    is_special = Flag("SPEC")   # Special rule with hard-coded behavior. Only referenced by ID.
    is_reference = Flag("REF")  # Rule used internally in other rules as a reference. Should not be matched directly.
    is_stroke = Flag("STRK")    # Exact match for a single stroke, not part of one. Handled by exact dict lookup.
    is_word = Flag("WORD")      # Exact match for a single word. These rules do not adversely affect lexer performance.
    is_rare = Flag("RARE")      # Rule applies to very few words and could specifically cause false positives.

    # Acceptable string values for graph and board element flags, as read from JSON or produced by the analyzer.
    is_inversion = Flag("INV")  # Inversion of steno order. Child rule keys will be out of order with respect to parent.
    is_linked = Flag("LINK")    # Rule that uses keys from two strokes. This complicates stroke delimiting.
    is_unmatched = Flag("BAD")  # Placeholder for keys inside a compound rule that do not belong to another child rule.

    def __init__(self, keys:str, letters:str, info:str, flags:AbstractSet[str]=frozenset(), r_id="", alt="") -> None:
        self.keys = keys        # Raw string of steno keys that make up the rule.
        self.letters = letters  # Raw English text of the word.
        self.info = info        # Textual description of the rule.
        self._flags = flags     # Set of string flags that apply to the rule.
        self._rulemap = []      # List of child rules mapped to letter positions *in order*.
        self.id = r_id          # Rule ID string. Used as a unique identifier. May be empty if dynamically generated.
        self.alt = alt          # Alternate text specifically for display in diagrams.

    def add_connection(self, child:"StenoRule", start:int, length:int) -> None:
        """ Connect a <child> rule to this one at <start>. Must be done in order. <length> may be 0. """
        item = self.Connection(child, start, length)
        self._rulemap.append(item)

    def add_unmatched(self, unmatched_keys:str) -> None:
        """ Add a placeholder child rule mapping leftover keys to an empty string of letters. """
        if self._rulemap:
            last_item = self._rulemap[-1]
            last_child_end = last_item.start + last_item.length
        else:
            last_child_end = 0
        remaining_length = len(self.letters) - last_child_end
        child = StenoRule(unmatched_keys, "", "unmatched keys", {StenoRule.is_unmatched})
        self.add_connection(child, last_child_end, remaining_length)

    def __bool__(self) -> bool:
        """ Return True if this rule is compound, meaning it is composed of smaller child rules. """
        return bool(self._rulemap)

    def __iter__(self) -> Iterator[Connection]:
        """ Yield each child rule connection in order. """
        return iter(self._rulemap)

    def __str__(self) -> str:
        """ The standard string representation of a rule is its keys -> letters mapping. """
        return f"{self.keys} → {self.letters}"

    def verify(self, valid_rtfcre:AbstractSet[str], delimiters:AbstractSet[str]) -> None:
        """ Perform integrity checks on this rule. """
        key_counter = Counter(self.keys)
        assert key_counter, f"Rule {self.id} is empty"
        # All key characters must be valid RTFCRE characters.
        assert (key_counter.keys() <= valid_rtfcre), f"Rule {self.id} has invalid characters"
        if self:
            # Check that the rulemap positions all fall within our own letter bounds.
            # Make sure the child rules contain all of our keys between them with no extras (except delimiters).
            for item in self:
                assert item.start >= 0
                assert item.length >= 0
                assert item.start + item.length <= len(self.letters)
                key_counter.subtract(item.child.keys)
            mismatched = [k for k in key_counter if key_counter[k] and k not in delimiters]
            assert not mismatched, f"Rule {self.id} has mismatched keys vs. its child rules: {mismatched}"


class StenoRuleParser:
    """ Converts steno rules from JSON arrays to StenoRule objects.
        In order to recursively resolve references, all rule data should be added before any parsing is done. """

    def __init__(self, sub_parser:TextSubstitutionParser=None) -> None:
        if sub_parser is None:
            sub_parser = TextSubstitutionParser()
        self._sub_parser = sub_parser  # Parser specifically for the pattern field.
        self._rule_data = {}           # Dict of other steno rule data fields from JSON.
        self._rule_memo = {}           # Memo of finished rules.

    def add_json_data(self, r_id:str, fields:list) -> None:
        """ Add JSON data for a single rule. The fields, in order, are:
            keys:    RTFCRE formatted string of steno strokes.
            pattern: English text pattern string, consisting of raw letters as well as references to other rules.
            flags:   Optional sequence of flag strings.
            info:    Optional info string for when the rule is displayed in the GUI. """
        try:
            keys, pattern, *optional = fields
        except ValueError as e:
            raise ValueError(f"Not enough data fields for rule {r_id}") from e
        flags = optional.pop(0) if optional else ()
        info = optional.pop(0) if optional else "No description"
        if optional:
            raise ValueError(f"Too many data fields for rule {r_id}: extra = {optional}")
        alt = ""
        if "(" not in pattern and "|" in pattern:
            pattern, alt = pattern.split("|", 1)
        self._sub_parser.add_mapping(r_id, pattern)
        self._rule_data[r_id] = [keys, flags, info, alt]

    def add_json_dict(self, d:dict) -> None:
        """ Add all rule data from a JSON dict. """
        if not isinstance(d, dict):
            raise TypeError('Rules data object is not a dict.')
        for name, data in d.items():
            self.add_json_data(name, data)

    def _parse(self, r_id:str) -> StenoRule:
        """ Return a rule by ID if finished, else parse it recursively. """
        memo = self._rule_memo
        if r_id in memo:
            return memo[r_id]
        keys, flags, info, alt = self._rule_data[r_id]
        sub_result = self._sub_parser.parse(r_id)
        rule = self._rule_memo[r_id] = StenoRule(keys, sub_result.text, info, set(flags), r_id, alt)
        for sub in sub_result.subs:
            child = self._parse(sub.ref)
            rule.add_connection(child, sub.start, sub.length)
        return rule

    def parse(self) -> List[StenoRule]:
        """ Parse all saved rule data and return the finished rules in a list. """
        return [self._parse(r_id) for r_id in self._rule_data]
