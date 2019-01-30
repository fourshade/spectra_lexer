from typing import FrozenSet, NamedTuple

from spectra_lexer.keys import StenoKeys


class RuleFlags:
    """ Acceptable string values for flags, as read from JSON, that indicate some property of a rule. """
    SPECIAL = "SPEC"   # Special rule used internally (in other rules). Only referenced by name.
    STROKE = "STRK"    # Exact match for a single stroke, not part of one. Handled by exact dict lookup.
    WORD = "WORD"      # Exact match for a single word. These rules do not adversely affect lexer performance.
    RARE = "RARE"      # Rule applies to very few words and could specifically cause false positives.
    GENERATED = "GEN"  # Lexer generated rule. This is always the root unless there are special circumstances.
    INVERSION = "INV"  # Inversion of steno order. Child rule keys will be out of order with respect to the parent.
    UNMATCHED = "BAD"  # Incomplete lexer result. This rule contains all the unmatched keys and no letters.
    SEPARATOR = "SEP"  # Stroke separator. This one might not be truly considered a rule at all.


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
