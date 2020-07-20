from collections import Counter
from typing import Container, Iterable, Iterator, List, Sequence

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
    is_reference = Flag("REF")  # Rule used internally in other rules as a reference. Should not be matched directly.
    is_stroke = Flag("STRK")    # Exact match for a single stroke, not part of one. Handled by exact dict lookup.
    is_word = Flag("WORD")      # Exact match for a single word. These rules do not adversely affect lexer performance.
    is_rare = Flag("RARE")      # Rule applies to very few words and could specifically cause false positives.

    # Acceptable string values for graph and board element flags, as read from JSON or produced by the analyzer.
    is_inversion = Flag("INV")  # Inversion of steno order. Child rule keys will be out of order with respect to parent.
    is_linked = Flag("LINK")    # Rule that uses keys from two strokes. This complicates stroke delimiting.
    is_unmatched = Flag("BAD")  # Placeholder for keys inside a compound rule that do not belong to another child rule.

    def __init__(self, keys:str, letters:str, info:str,
                 flags:Container[str], rulemap:Sequence[Connection], r_id:str, alt:str) -> None:
        self.keys = keys         # RTFCRE steno keys that make up the rule.
        self.letters = letters   # Raw English text of the word.
        self.info = info         # Textual description of the rule.
        self._flags = flags      # Set of string flags that apply to the rule.
        self._rulemap = rulemap  # Sequence of child rules mapped to letter positions *in order*.
        self.id = r_id           # Rule ID string. Used as a unique identifier. May be empty if dynamically generated.
        self.alt = alt           # Alternate text specifically for display in diagrams.

    def __bool__(self) -> bool:
        """ Return True if this rule is compound, meaning it is composed of smaller child rules. """
        return bool(self._rulemap)

    def __iter__(self) -> Iterator[Connection]:
        """ Yield each child rule connection in order. """
        return iter(self._rulemap)

    def __repr__(self) -> str:
        """ The standard string representation of a rule is its keys -> letters mapping. """
        return f'<StenoRule: {self.keys} → {self.letters}>'

    __str__ = __repr__

    def verify(self, valid_rtfcre:Iterable[str], delimiters:Iterable[str]) -> None:
        """ Perform integrity checks on this rule. """
        key_set = set(self.keys)
        assert key_set, f"Rule {self.id} is empty"
        # All key characters must be valid RTFCRE characters.
        invalid = key_set.difference(valid_rtfcre)
        assert not invalid, f"Rule {self.id} has invalid characters: {invalid}"
        if self:
            # Check that the rulemap positions all fall within our own letter bounds.
            # Start positions must be non-negative and increasing monotonic.
            counter = Counter(self.keys)
            last_start = 0
            for item in self:
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

    def build(self, keys:str, letters:str, info:str, flags:Container[str]=frozenset(), r_id="", alt="") -> StenoRule:
        """ Pop the current rulemap from the stack and build a new rule using it. """
        rulemap = self._head
        self._head = self._stack.pop()
        return self._rule_cls(keys, letters, info, flags, rulemap, r_id, alt)

    def connect(self, child:StenoRule, start:int, length:int) -> None:
        """ Add a <child> rule to the rulemap at <start>. Must be done in order. <length> may be 0. """
        item = self._rule_cls.Connection(child, start, length)
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
        info = f'{unmatched_keys}: unmatched keys'
        flags = {self._rule_cls.is_unmatched}
        child = self.build(unmatched_keys, "", info, flags)
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
        info = f'{keys} → {letters}'
        return self.build(keys, letters, info)


StenoRuleList = List[StenoRule]


class StenoRuleParser:
    """ Converts steno rules from JSON arrays to StenoRule objects.
        In order to recursively resolve references, all rule data should be added before any parsing is done. """

    def __init__(self, factory:StenoRuleFactory, *, sub_parser:TextSubstitutionParser=None) -> None:
        if sub_parser is None:
            sub_parser = TextSubstitutionParser()
        self._factory = factory        # Creates steno rules from JSON data.
        self._sub_parser = sub_parser  # Parser specifically for the pattern field.
        self._rule_data = {}           # Dict of other steno rule data fields from JSON.
        self._rule_memo = {}           # Memo of finished rules.

    def add_json_data(self, r_id:str, fields:list) -> None:
        """ Add JSON data for a single rule. The fields, in order, are:
            keys:    RTFCRE formatted string of steno strokes.
            pattern: English text pattern string, consisting of raw letters as well as references to other rules.
            flags:   Optional sequence of flag strings.
            desc:    Optional description string for when the rule is displayed in the GUI. """
        try:
            keys, pattern, *optional = fields
        except ValueError as e:
            raise ValueError(f"Not enough data fields for rule {r_id}") from e
        flags = frozenset(optional.pop(0) if optional else ())
        desc = optional.pop(0) if optional else "No description"
        if optional:
            raise ValueError(f"Too many data fields for rule {r_id}: extra = {optional}")
        alt = ""
        if "(" not in pattern and "|" in pattern:
            pattern, alt = pattern.split("|", 1)
        self._sub_parser.add_mapping(r_id, pattern)
        self._rule_data[r_id] = [keys, flags, desc, alt]

    def _parse(self, r_id:str) -> StenoRule:
        """ Return a rule by ID if finished, else parse it recursively. """
        memo = self._rule_memo
        if r_id in memo:
            return memo[r_id]
        keys, flags, desc, alt = self._rule_data[r_id]
        sub_result = self._sub_parser.parse(r_id)
        subs = sub_result.subs
        letters = sub_result.text
        if subs and letters:
            # Compound rule info includes the complete mapping of keys to letters.
            info = f'{keys} → {letters}: {desc}'
        else:
            # Base rule info includes only the keys to the left of the description.
            info = f'{keys}: {desc}'
        self._factory.push()
        for sub in subs:
            child = self._parse(sub.ref)
            self._factory.connect(child, sub.start, sub.length)
        rule = memo[r_id] = self._factory.build(keys, letters, info, flags, r_id, alt)
        return rule

    def parse(self) -> StenoRuleList:
        """ Parse all saved rule data and return the finished rules in a list. """
        return [self._parse(r_id) for r_id in self._rule_data]
