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


# Rule constants governing key flags.
_KEY_RULES = {k: StenoRule(StenoKeys.from_rtfcre(k.split(":", 1)[0]), "", frozenset(), v, ())
              for (k, v) in KEY_FLAGS.items()}


def add_key_rules(m:List[RuleMapItem], flags:Iterable[str], start:int) -> None:
    """ Add key rules from the given flags (only if they are key flags).
        It is possible that there is more than one; in that case, advance one space each time. """
    rules = [_KEY_RULES[f] for f in flags if f in _KEY_RULES]
    m.extend([RuleMapItem(r, start + i, 0) for i, r in enumerate(rules)])
