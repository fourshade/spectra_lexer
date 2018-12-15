from operator import attrgetter
from typing import Iterable, List, NamedTuple, Sequence, Set

from spectra_lexer.keys import KEY_SEP, StenoKeys

# Acceptable rule flags that provide specific meanings to a key (usually the asterisk).
# Each of these will be transformed into a special rule that appears at the end of a result.
KEY_FLAGS = {"*:??":  "purpose unknown\nPossibly resolves a conflict",
             "*:CF":  "resolves conflict between words",
             "*:PR":  "indicates a proper noun\n(names, places, etc.)",
             "*:AB":  "indicates an abbreviation",
             "*:PS":  "indicates a prefix or suffix stroke",
             "*:OB":  "indicates an obscenity\n(and make it harder to be the result of a misstroke)",
             "*:FS":  "indicates fingerspelling",
             "p:FS":  "use to capitalize fingerspelled letters",
             "#:NM":  "use to shift to number mode",
             "EU:NM": "use to invert the order of two digits",
             "d:NM":  "use to double a digit"}
KEY_FLAG_SET = set(KEY_FLAGS.keys())


class _MapItem(NamedTuple):
    """ Data structure specifying the parent attach positions for a rule. """
    rule: 'StenoRule'
    start: int
    length: int


class RuleMap(List[_MapItem]):
    """ List subclass meant to hold a series of (rule, start, length) tuples indicating
        the various rules that make up a word and their starting/ending positions. """

    def add_child(self, rule:'StenoRule', start:int, length:int) -> None:
        """ Add a single rule to the end of the map. """
        self.append(_MapItem(rule, start, length))

    def add_key_rules(self, flags:Set[str], start:int, remove_flags:bool=False) -> None:
        """ Add key rules to the end of the rulemap from the given flags (only if they are key flags).
            If remove_flags is True, remove the key flags we used from the source container. """
        key_flags = flags & KEY_FLAG_SET
        for f in key_flags:
            self.append(_MapItem(_KEY_RULES[f], start, 0))
        if remove_flags:
            flags -= key_flags

    def add_separator(self, start:int) -> None:
        """ Add a stroke separator rule to the rulemap at the given position. """
        self.append(_MapItem(_RULE_SEP, start, 0))

    def ends_with_separator(self) -> bool:
        """ Is the final rule a stroke separator? """
        return self[-1].rule.is_separator()

    def rules(self, agetter=attrgetter("rule")) -> Iterable['StenoRule']:
        """ Iterator that returns every rule in sequence. """
        return map(agetter, self)

    def keys_matched(self, agetter=attrgetter("rule.keys")) -> int:
        """ Get the total number of keys matched by mapped rules. """
        return sum(map(len, map(agetter, self)))

    def letters_matched(self,  agetter=attrgetter("rule.letters")) -> int:
        """ Get the total number of characters matched by mapped rules. """
        return sum(map(len, map(agetter, self)))

    def word_coverage(self) -> int:
        """ Return the number of characters between the start of the first child rule and the end of the last. """
        if self:
            start_item = self[0]
            end_item = self[-1]
            return end_item.start + end_item.length - start_item.start
        return 0

    def rank(self) -> Sequence[int]:
        """
        Determine the "rank" of a rule map for sorting of lexer output. A larger value
        should reflect a more accurate mapping. Assuming all keys are matched,
        rank value is determined by a tuple of these values, in order:
            - most letters matched
            - fewest child rules
            - end-to-end word coverage
        """
        return self.letters_matched(), -len(self), self.word_coverage()

    @classmethod
    def best_map(cls, maps:Iterable[__qualname__]) -> __qualname__:
        """ Return the best out of a series of rule maps based on the rank value of each.
            Return an empty map if the iterable is empty. """
        return max(maps, key=cls.rank, default=_RULEMAP_EMPTY)


# Empty rulemap constant to be used as a default value. Should never be modified.
_RULEMAP_EMPTY = RuleMap()


class StenoRule(NamedTuple):
    """ A general rule mapping a set of steno keys to a set of letters.
        May include flags, a description, and/or a submapping of rules that compose it. """

    keys: StenoKeys    # String of steno keys that make up the rule, pre-parsed and sorted.
    letters: str       # Raw English text of the word.
    flags: Set[str]    # Set of strings describing flags that apply to the rule.
    desc: str          # Textual description of the rule.
    rulemap: RuleMap   # List of tuples mapping child rules to letter positions.

    def is_separator(self) -> bool:
        """ Is the current rule a stroke separator? """
        return self is _RULE_SEP

    @classmethod
    def from_lexer_result(cls, keys:StenoKeys, letters:str, rulemap:RuleMap) -> __qualname__:
        """ Make a new rule from output parameters given by the lexer. """
        if rulemap:
            matchable_letters = sum(c is not ' ' for c in letters)
            if matchable_letters:
                percent_match = rulemap.letters_matched() * 100 / matchable_letters
            else:
                percent_match = 0
            desc = "Found {:d}% match.".format(int(percent_match))
        else:
            desc = "No matches found."
        return cls(keys, letters, set(), desc, rulemap)

    @classmethod
    def best_rule(cls, rules:Iterable[__qualname__]) -> __qualname__:
        """ Return the best out of a series of rules based on the rank value of each map.
            max() will throw an exception if the iterable is empty. """
        r_list = list(rules)
        maps = [r.rulemap for r in r_list]
        best_map = RuleMap.best_map(maps)
        return r_list[maps.index(best_map)]

    def __str__(self) -> str:
        return "{} → {}".format(self.keys.inv_parse(), self.letters)

    def __repr__(self) -> str:
        return str(self._asdict())


# Rule constants governing separators and star flags.
_RULE_SEP = StenoRule(StenoKeys(KEY_SEP), "", {"SPEC"}, "Stroke separator", _RULEMAP_EMPTY)
_KEY_RULES = {k: StenoRule(StenoKeys(k.split(":", 1)[0]), "", {"KEY"}, v, _RULEMAP_EMPTY) for (k, v) in KEY_FLAGS.items()}
