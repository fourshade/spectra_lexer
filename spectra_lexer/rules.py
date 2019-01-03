from typing import FrozenSet, NamedTuple

from spectra_lexer.keys import StenoKeys


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
