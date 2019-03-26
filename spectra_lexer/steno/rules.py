from typing import FrozenSet, NamedTuple

from .keys import KEY_SPECIAL, StenoKeys
from spectra_lexer.utils import with_sets


@with_sets
class RuleFlags:
    """ Acceptable string values for flags, as read from JSON, that indicate some property of a rule. """
    SPECIAL = "SPEC"   # Special rule used internally (in other rules). Only referenced by name.
    STROKE = "STRK"    # Exact match for a single stroke, not part of one. Handled by exact dict lookup.
    WORD = "WORD"      # Exact match for a single word. These rules do not adversely affect lexer performance.
    RARE = "RARE"      # Rule applies to very few words and could specifically cause false positives.
    INVERSION = "INV"  # Inversion of steno order. Child rule keys will be out of order with respect to the parent.
    UNMATCHED = "BAD"  # Incomplete lexer result. This rule contains all the unmatched keys and no letters.
    GENERATED = "GEN"  # Lexer generated rule. This is always the root unless there are special circumstances.


class StenoRule(NamedTuple):
    """ A general rule mapping a set of steno keys to a set of letters. All contents are immutable.
        Includes flags, a description, and a submapping of rules that compose it. """

    keys: StenoKeys        # String of steno keys that make up the rule, pre-parsed and sorted.
    letters: str           # Raw English text of the word.
    flags: FrozenSet[str]  # Immutable set of strings describing flags that apply to the rule.
    desc: str              # Textual description of the rule.
    rulemap: tuple         # Tuple of tuples mapping child rules to letter positions.

    def __str__(self) -> str:
        return f"{self.keys.rtfcre} → {self.letters}"


class RuleMapItem(NamedTuple):
    """ Immutable data structure specifying the parent attach positions for a rule. """
    rule: StenoRule
    start: int
    length: int


class SpecialRules:
    """ Class with identifiers for various special rules so they can be handled individually in code.
        These always go at the end of rule patterns (in regular parentheses ()) regardless of steno order. """

    ALL = {}  # Special rules that have hard-coded behavior. Every rule dict will include these by default.

    def _star_rule(name, desc:str, _d=ALL) -> StenoRule:
        """ Make a new "star rule": one that does not correspond to any letters, and add it to the global dict. """
        rule = StenoRule(StenoKeys(KEY_SPECIAL), "", frozenset({RuleFlags.SPECIAL}), desc, ())
        _d[f"{KEY_SPECIAL}:{name}"] = rule
        return rule

    UNKNOWN = _star_rule("??",      "purpose unknown\nPossibly resolves a conflict")
    CONFLICT = _star_rule("CF",     "resolves conflict between words")
    PROPER = _star_rule("PR",       "indicates a proper noun\n(names, places, etc.)")
    ABBREVIATION = _star_rule("AB", "indicates an abbreviation")
    AFFIX = _star_rule("PS",        "indicates a prefix or suffix stroke")
    FINGERSPELL = _star_rule("FS",  "indicates fingerspelling")
    OBSCENE = _star_rule("OB",      "indicates an obscenity\nand makes it harder to be the result of a misstroke)")
