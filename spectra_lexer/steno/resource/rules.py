from typing import NamedTuple


class RuleFlags(frozenset):
    """ Immutable set of string flags that each indicate some property of a rule. """

    # These are the acceptable string values for flags, as read from JSON.
    SPECIAL = "SPEC"   # Special rule used internally (in other rules). Only referenced by name.
    STROKE = "STRK"    # Exact match for a single stroke, not part of one. Handled by exact dict lookup.
    WORD = "WORD"      # Exact match for a single word. These rules do not adversely affect lexer performance.
    RARE = "RARE"      # Rule applies to very few words and could specifically cause false positives.
    OPTIONAL = "OPT"   # Optional or redundant rule. May be informational; removal will cause little effect.
    INVERSION = "INV"  # Inversion of steno order. Child rule keys will be out of order with respect to the parent.
    LINKED = "LINK"    # Rule that uses keys from two strokes. This complicates stroke delimiting.
    UNMATCHED = "BAD"  # Incomplete lexer result. This rule contains all the unmatched keys and no letters.
    GENERATED = "GEN"  # Lexer generated rule. This is always the root unless there are special circumstances.

    VALID_FLAGS = {v for v in locals().values() if type(v) is str}  # Contains all valid string values above.

    def get_invalid(self) -> frozenset:
        """ Return any flags in the set that are not defined as constants above. """
        return self - self.VALID_FLAGS


class StenoRule(NamedTuple):
    """ A general rule mapping a set of steno keys to a set of letters. All contents are recursively immutable.
        Includes flags, a description, and a submapping of rules that compose it. """

    keys: str         # Raw string of steno keys that make up the rule.
    letters: str      # Raw English text of the word.
    flags: RuleFlags  # Immutable set of strings describing flags that apply to the rule.
    desc: str         # Textual description of the rule.
    rulemap: tuple    # Immutable sequence of tuples mapping child rules to letter positions *in order*.

    def __str__(self) -> str:
        """ The standard string representation of a rule is just its mapping of keys to letters. """
        return f"{self.keys} → {self.letters or '<special>'}"

    def caption(self) -> str:
        """ Generate a plaintext caption for a rule based on its child rules and flags. """
        description = self.desc
        # Lexer-generated rules display only the description by itself.
        if RuleFlags.GENERATED in self.flags:
            return description
        # Base rules (i.e. leaf nodes) display their keys to the left of their descriptions.
        if not self.rulemap:
            return f"{self.keys}: {description}"
        # Derived rules (i.e. non-leaf nodes) show the complete mapping of keys to letters in their description.
        return f"{self}: {description}"


class RuleMapItem(NamedTuple):
    """ Immutable data structure specifying the parent attach positions for a rule. """
    rule: StenoRule
    start: int
    length: int
