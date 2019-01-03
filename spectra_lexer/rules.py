from typing import FrozenSet, Iterable, List, NamedTuple

from spectra_lexer.keys import StenoKeys

# Acceptable rule flags that provide specific meanings to a key (usually the asterisk).
# Each of these will be transformed into a special rule that appears at the end of a result.
KEY_FLAGS = {"*:??":  "purpose unknown\nPossibly resolves a conflict",
             "*:CF":  "resolves conflict between words",
             "*:PR":  "indicates a proper noun\n(names, places, etc.)",
             "*:AB":  "indicates an abbreviation",
             "*:PS":  "indicates a prefix or suffix stroke",
             "*:OB":  "indicates an obscenity\n(and make it harder to be the result of a misstroke)",
             "*:FS":  "indicates fingerspelling",
             "-P:FS":  "use to capitalize fingerspelled letters",
             "#:NM":  "use to shift to number mode",
             "EU:NM": "use to invert the order of two digits",
             "-D:NM":  "use to double a digit"}


class StenoRule(NamedTuple):
    """ A general rule mapping a set of steno keys to a set of letters. All contents are immutable.
        Includes flags, a description, and a submapping of rules that compose it. """

    keys: StenoKeys        # String of steno keys that make up the rule, pre-parsed and sorted.
    letters: str           # Raw English text of the word.
    flags: FrozenSet[str]  # Immutable set of strings describing flags that apply to the rule.
    desc: str              # Textual description of the rule.
    rulemap: tuple         # Tuple of tuples mapping child rules to letter positions.

    def __str__(self) -> str:
        return "{} → {}".format(self.keys.to_rtfcre(), self.letters)


class RuleMapItem(NamedTuple):
    """ Immutable data structure specifying the parent attach positions for a rule. """
    rule: StenoRule
    start: int
    length: int


class RuleMap(List[RuleMapItem]):
    """ List-based rulemap: a sequence meant to hold a series of (rule, start, length) tuples
        indicating the various rules that make up a word and their starting/ending positions.
        Map items should be in sequential order by starting position within the word.
        Must be frozen before inclusion in a rule. """

    def add(self, rule:StenoRule, start:int, length:int) -> None:
        """ Add a single rule to the end of the map. """
        self.append(RuleMapItem(rule, start, length))

    def add_special(self, rule:StenoRule, start:int) -> None:
        """ Add a single special zero-length rule to the end of the map. """
        self.append(RuleMapItem(rule, start, 0))

    def freeze(self):
        """ Freeze the rule map for inclusion in an immutable rule. """
        return tuple(self)


# Rule constants governing key flags.
_KEY_RULES = {k: StenoRule(StenoKeys.from_rtfcre(k.split(":", 1)[0]), "", frozenset(), v, ())
              for (k, v) in KEY_FLAGS.items()}


def get_key_rules(flags:Iterable[str]) -> List[StenoRule]:
    """ Get key rules from the given flags (only if they are key flags). """
    return [_KEY_RULES[f] for f in flags if f in _KEY_RULES]
