""" Package for components comprising the primary steno analysis component - the lexer.
    All steno key input is required to be in 's-keys' string format, which has the following requirements:

    - Every key in a stroke is represented by a single distinct character (in contrast to RTFCRE).
    - Strokes are delimited by a single distinct character.
    - The keys within each stroke must be sorted according to some total ordering (i.e. steno order). """

from typing import Iterable, Tuple


class LexerRule:
    """ Lexer rule data. Must be interpreted by rule matchers. """

    def __init__(self, skeys:str, letters:str, weight:int) -> None:
        self.skeys = skeys      # Steno keys matched by the rule, in "s-keys" format (one unique character per key).
        self.letters = letters  # Orthographic characters (i.e. English letters) matched by the rule.
        self.weight = weight    # Weighting level for accuracy comparisons.

    def __repr__(self) -> str:
        return f'LexerRule{(self.skeys, self.letters, self.weight)!r}'


RuleMatch = Tuple[LexerRule, str, int]  # Rule match data type: (rule, unmatched keys, start offset in word).
RuleMatches = Iterable[RuleMatch]       # Iterable of rule matches (with no particular ordering).


class IRuleMatcher:
    """ Interface for a class that matches steno rules using a rule's s-keys and/or letters. """

    def match(self, skeys:str, letters:str, all_skeys:str, all_letters:str) -> RuleMatches:
        raise NotImplementedError
