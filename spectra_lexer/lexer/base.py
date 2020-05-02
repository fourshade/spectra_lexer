from typing import Iterable, Tuple


class LexerRule:
    """ Lexer rule data. Must be interpreted by rule matchers. """

    def __init__(self, skeys:str, letters:str, weight:int) -> None:
        self.skeys = skeys      # Steno keys matched by the rule, in "s-keys" format (one unique character per key).
        self.letters = letters  # Orthographic characters (i.e. English letters) matched by the rule.
        self.weight = weight    # Weighting level for accuracy comparisons.

    def __repr__(self) -> str:
        return f'LexerRule{(self.skeys, self.letters, self.weight)!r}'


# Rule match data type: (rule, unmatched keys, start offset in word).
RuleMatch = Tuple[LexerRule, str, int]


class IRuleMatcher:
    """ Interface for a class that matches steno rules using a rule's s-keys and/or letters. """

    def match(self, skeys:str, letters:str, all_skeys:str, all_letters:str) -> Iterable[RuleMatch]:
        raise NotImplementedError
