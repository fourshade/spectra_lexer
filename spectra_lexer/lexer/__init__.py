""" Package for components comprising the primary steno analysis component - the lexer.
    All steno key input is required to be in 's-keys' string format, which has the following requirements:

    - Every key in a stroke is represented by a single distinct character (in contrast to RTFCRE).
    - Strokes are delimited by a single distinct character.
    - The keys within each stroke must be sorted according to some total ordering (i.e. steno order). """

from typing import Iterable, Tuple


class IRule:
    """ Abstract lexer rule data. Must be interpreted by rule matchers. """

    skeys: str    # Steno keys matched by the rule, in "s-keys" format (one unique character per key).
    letters: str  # Orthographic characters (i.e. English letters) matched by the rule.


RuleMatch = Tuple[IRule, str, int]  # Rule match data type: (rule, unmatched keys, start offset in word).
RuleMatches = Iterable[RuleMatch]   # Iterable of rule matches (with no particular ordering).


class IRuleMatcher:
    """ Interface for a class that matches steno rules using a rule's s-keys and/or letters. """

    def match(self, skeys:str, letters:str, all_skeys:str, all_letters:str) -> RuleMatches:
        raise NotImplementedError
