from collections import Counter
from typing import AbstractSet, Dict, Iterable, Iterator, List

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
    is_special = Flag("SPEC")   # Special rule used internally (in other rules). Only referenced by name.
    is_stroke = Flag("STRK")    # Exact match for a single stroke, not part of one. Handled by exact dict lookup.
    is_word = Flag("WORD")      # Exact match for a single word. These rules do not adversely affect lexer performance.
    is_rare = Flag("RARE")      # Rule applies to very few words and could specifically cause false positives.

    # Acceptable string values for graph and board element flags, as read from JSON or produced by the analyzer.
    is_separator = Flag("SEP")  # Stroke separator rule.
    is_inversion = Flag("INV")  # Inversion of steno order. Child rule keys will be out of order with respect to parent.
    is_linked = Flag("LINK")    # Rule that uses keys from two strokes. This complicates stroke delimiting.
    is_unmatched = Flag("BAD")  # Placeholder for keys inside a compound rule that do not belong to another child rule.

    def __init__(self, r_id:str, keys:str, letters:str, info:str, flags:AbstractSet[str], alt="") -> None:
        self.id = r_id          # Rule ID string. Used as a unique identifier. May be empty if dynamically generated.
        self.keys = keys        # Raw string of steno keys that make up the rule.
        self.letters = letters  # Raw English text of the word.
        self.info = info        # Textual description of the rule.
        self._flags = flags     # Set of string flags that apply to the rule.
        self._rulemap = []      # List of child rules mapped to letter positions *in order*.
        self.alt = alt          # Alternate text specifically for display in diagrams.

    def add_connection(self, child:"StenoRule", start:int, length:int) -> None:
        """ Connect a <child> rule to this one at <start>. Must be done in order. <length> may be 0. """
        item = self.Connection(child, start, length)
        self._rulemap.append(item)

    def __bool__(self) -> bool:
        """ Return True if this rule is compound, meaning it is composed of smaller child rules. """
        return bool(self._rulemap)

    def __iter__(self) -> Iterator[Connection]:
        """ Yield each child rule connection in order. """
        return iter(self._rulemap)

    def __str__(self) -> str:
        """ The standard string representation of a rule is its keys -> letters mapping. """
        return f"{self.keys} → {self.letters}"

    def verify(self, valid_keys:AbstractSet[str], delimiters:AbstractSet[str]) -> None:
        """ Perform integrity checks on this rule. """
        key_counter = Counter(self.keys)
        assert key_counter, f"Rule {self.id} is empty"
        # All keys must be valid RTFCRE characters.
        assert (key_counter.keys() <= valid_keys), f"Rule {self.id} has invalid keys"
        if self:
            # Check that the rulemap positions all fall within the legal bounds (i.e. within the parent's letters)
            # Make sure the child rules contain all the keys of the parent between them, and no extras.
            parent_len = len(self.letters)
            for item in self:
                assert item.start >= 0
                assert item.length >= 0
                assert item.start + item.length <= parent_len
                keys = item.child.keys
                key_counter.subtract(keys)
            mismatched = [k for k in key_counter if key_counter[k] and k not in delimiters]
            assert not mismatched, f"Rule {self.id} has mismatched keys vs. its child rules: {mismatched}"

    @classmethod
    def analysis(cls, keys:str, letters:str, info:str) -> "StenoRule":
        return cls("", keys, letters, info, set())

    @classmethod
    def unmatched(cls, keys:str) -> "StenoRule":
        """ Return a placeholder rule mapping leftover keys from a lexer result to an empty string of letters. """
        return cls("", keys, "", "unmatched keys", {cls.is_unmatched})


class StenoRuleParser:
    """ Converts steno rules from JSON arrays to StenoRule objects.
        In order to recursively resolve references, all rule data should be added before any parsing is done. """

    def __init__(self, sub_parser:TextSubstitutionParser) -> None:
        self._sub_parser = sub_parser  # Parser specifically for the pattern field.
        self._rule_data = {}           # Dict of other steno rule data fields from JSON.

    def add_rule_data(self, id:str, data:Iterable) -> None:
        """ Add JSON data for a single rule. The fields, in order, are:
            keys:    RTFCRE formatted string of steno strokes.
            pattern: English text pattern string, consisting of raw letters as well as references to other rules.
            flags:   Optional sequence of flag strings.
            info:    Optional info string for when the rule is displayed in the GUI. """
        try:
            keys, pattern, *optional = data
        except ValueError as e:
            raise ValueError(f"Not enough data fields for rule {id}") from e
        flags = optional.pop(0) if optional else ()
        info = optional.pop(0) if optional else "No description"
        if optional:
            raise ValueError(f"Too many data fields for rule {id}: extra = {optional}")
        alt = ""
        if "(" not in pattern and "|" in pattern:
            pattern, alt = pattern.split("|", 1)
        self._sub_parser.add_mapping(id, pattern)
        self._rule_data[id] = [keys, flags, info, alt]

    def parse(self) -> List[StenoRule]:
        """ Parse all saved rule data recursively and return the finished rules in a list. """
        memo = {}
        return [self._parse(r_id, memo) for r_id in self._rule_data]

    def _parse(self, r_id:str, memo:Dict[str, StenoRule]) -> StenoRule:
        if r_id in memo:
            return memo[r_id]
        keys, flags, info, alt = self._rule_data[r_id]
        sub_result = self._sub_parser.parse(r_id)
        rule = memo[r_id] = StenoRule(r_id, keys, sub_result.text, info, set(flags), alt)
        for sub in sub_result.subs:
            child = self._parse(sub.ref, memo)
            rule.add_connection(child, sub.start, sub.length)
        return rule


class StenoRuleCollection:
    """ Immutable iterable collection of steno rules. """

    def __init__(self, rules:Iterable[StenoRule]) -> None:
        self._rules = rules

    def __iter__(self) -> Iterator[StenoRule]:
        """ Iterate through every rule in order. """
        return iter(self._rules)

    def verify(self, valid_keys:Iterable[str], delimiters:Iterable[str]) -> None:
        """ Go through each rule and perform integrity checks. """
        valid_keys = set(valid_keys)
        delimiters = set(delimiters)
        for rule in self:
            rule.verify(valid_keys, delimiters)

    @classmethod
    def from_dict(cls, d:Dict[str, Iterable]) -> "StenoRuleCollection":
        """ Return a rule collection parsed from a standard dict. """
        if not isinstance(d, dict) or not all([hasattr(v, "__iter__") for v in d.values()]):
            raise TypeError('Rules data object is not a dict of iterables.')
        sub_parser = TextSubstitutionParser()
        parser = StenoRuleParser(sub_parser)
        for name, data in d.items():
            parser.add_rule_data(name, data)
        rules = parser.parse()
        return cls(rules)
