from collections import Counter
from typing import Iterable, Sequence

from . import FrozenStruct


class StenoRule(FrozenStruct):
    """ Immutable structure for a rule mapping a set of steno keys to a set of letters. There are two major types:
        Simple/base - a fundamental rule mapping a set of keys to letters. These have no children.
        Compound/derived - a more complex rule composed of simple or even other compound rules recursively.
        For compound rules, every key in the parent should be used by exactly one child. """

    class Connection(FrozenStruct):
        """ Contains a child rule and where it fits within the parent. """
        child: "StenoRule"  # Child rule object.
        start: int          # Index of the first letter in the parent where the child attaches.
        length: int         # Number of letters that the child spans in the parent.

    Rulemap = Sequence[Connection]

    # Required attributes:
    keys: str         # RTFCRE steno keys that make up the rule.
    letters: str      # Raw English text of the word.
    info: str         # Textual description of the rule.
    id: str           # Rule ID string. Used as a unique identifier. May be empty if dynamically generated.
    alt: str          # Alternate text specifically for display in diagrams.
    rulemap: Rulemap  # Sequence of child rules mapped to letter positions *in order*.

    # Lexer-related flags:
    is_reference = False  # Used internally in other rules as a reference. Should not be matched directly.
    is_stroke = False     # Exact match for a single stroke, not part of one. Handled by exact dict lookup.
    is_word = False       # Exact match for a single word (whitespace separated).
    is_rare = False       # Applies to very few words and could specifically cause false positives.

    # Appearance-related flags:
    is_inversion = False  # Inversion of steno order. Child rule keys will be out of order with respect to parent.
    is_linked = False     # Uses keys from two strokes. This complicates stroke delimiting.
    is_unmatched = False  # Placeholder for keys inside a compound rule that do not belong to another child rule.

    def verify(self, valid_rtfcre:Iterable[str], delimiters:Iterable[str]) -> None:
        """ Perform integrity checks on this rule. """
        key_set = set(self.keys)
        assert key_set, f"Rule {self.id} is empty"
        # All key characters must be valid RTFCRE characters.
        invalid = key_set.difference(valid_rtfcre)
        assert not invalid, f"Rule {self.id} has invalid characters: {invalid}"
        if self.rulemap:
            # Check that the rulemap positions all fall within our own letter bounds.
            # Start positions must be non-negative and increasing monotonic.
            counter = Counter(self.keys)
            last_start = 0
            for item in self.rulemap:
                start = item.start
                assert start >= last_start
                last_start = start
                length = item.length
                assert length >= 0
                assert start + length <= len(self.letters)
                counter.subtract(item.child.keys)
            # Make sure the child rules contain all of our keys between them with no extras (except delimiters).
            for k in delimiters:
                del counter[k]
            assert not +counter, f"Rule {self.id} has more keys than its child rules: {+counter}"
            assert not -counter, f"Rule {self.id} has fewer keys than its child rules: {-counter}"


class StenoRuleFactory:

    def __init__(self, *, rule_cls=StenoRule) -> None:
        self._rule_cls = rule_cls
        self._head = []   # Current rulemap; the head of the stack.
        self._stack = []  # The rest of the stack.

    def push(self) -> None:
        """ Push a new rulemap onto the stack. """
        self._stack.append(self._head)
        self._head = []

    def build(self, keys:str, letters:str, info:str, alt="", r_id="", **flags:bool) -> StenoRule:
        """ Pop the current rulemap from the stack and build a new rule using it. """
        rulemap = tuple(self._head)
        self._head = self._stack.pop()
        return self._rule_cls(keys=keys, letters=letters, info=info, alt=alt, id=r_id, rulemap=rulemap, **flags)

    def connect(self, child:StenoRule, start:int, length:int) -> None:
        """ Add a <child> rule to the rulemap at <start>. Must be done in order. <length> may be 0. """
        item = self._rule_cls.Connection(child=child, start=start, length=length)
        self._head.append(item)

    def connect_unmatched(self, unmatched_keys:str, nletters:int) -> None:
        """ Add a special (empty) rule at the end with <unmatched_keys> taking up the rest of <nletters>. """
        if self._head:
            last_item = self._head[-1]
            last_child_end = last_item.start + last_item.length
        else:
            last_child_end = 0
        remaining_length = nletters - last_child_end
        self.push()
        child = self.build(unmatched_keys, "", "unmatched keys", is_unmatched=True)
        self.connect(child, last_child_end, remaining_length)

    def join(self, rules:Iterable[StenoRule]) -> StenoRule:
        """ Join several rules into one. """
        keys = letters = ""
        offset = 0
        self.push()
        for r in rules:
            keys += r.keys
            letters += r.letters
            length = len(r.letters)
            self.connect(r, offset, length)
            offset += length
        return self.build(keys, letters, "combined rules")
