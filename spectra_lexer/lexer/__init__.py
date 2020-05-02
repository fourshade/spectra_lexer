""" Package for components comprising the primary steno analysis component - the lexer.
    All steno key input is required to be in 's-keys' string format, which has the following requirements:

    - Every key in a stroke is represented by a single distinct character (in contrast to RTFCRE).
    - Strokes are delimited by a single distinct character.
    - The keys within each stroke must be sorted according to some total ordering (i.e. steno order). """

from .base import IRuleMatcher, LexerRule, RuleMatch
from .lexer import LexerResult, StenoLexer
