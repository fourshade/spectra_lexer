from collections import defaultdict
from functools import reduce
from typing import Iterable, TypeVar

from spectra_lexer.keys import KEY_NUMBER, StenoKeys, L_KEYS, C_KEYS, R_KEYS, KEY_SEP, KEY_SPLIT, first_stroke
from spectra_lexer.utils import nop

# Steno keys required to produce the numbers 0-9 in order (with the number key).
NUMBER_ALIASES = "OSTPHAfplt"
NUMBER_LITERALS_IN = set(map(str, range(10))).intersection
# Translation table for cleansing steno strings of unknown origin.
VALID_CHAR_SET = set().union(L_KEYS, C_KEYS, R_KEYS, R_KEYS.upper(), KEY_SEP, KEY_SPLIT)
TF_DICT = defaultdict(nop, {ord(k): k for k in VALID_CHAR_SET})
TF_DICT.update(enumerate(NUMBER_ALIASES, ord("0")))

# Steno order is not enforced for any keys in this set. This has a large performance and accuracy cost.
# Only the asterisk is used in such a way that this treatment is worth it.
KEY_STAR = "*"
UNORDERED_KEYS = frozenset({KEY_STAR})
UNORDERED_KEYS_IN = UNORDERED_KEYS.intersection


T = TypeVar('LexerKeys')
class LexerKeys(StenoKeys):
    """ Special subclass of LexerKeys with attributes for rule matching and copy+mutate methods.
        Tracks "ordered" and "unordered" keys independently of the full set in the base string. """

    ordered: str = ""                   # Ordered string of normal keys that must be consumed starting from the left.
    unordered: frozenset = frozenset()  # Unordered keys in the current stroke that may be consumed at any time.

    def __init__(self, keys:str):
        """ Create the base string with all keys, then use that to start an ordered copy.
            Filter the unordered keys out of that and save it for use as a dict key.
            Keys must already be in dehyphenated, case-distinct format. """
        if not UNORDERED_KEYS_IN(keys):
            self.ordered = keys
        else:
            self.unordered = UNORDERED_KEYS_IN(first_stroke(keys))
            self.ordered = _remove_chars(keys, self.unordered)

    def without(self, keys:str) -> T:
        """ Return a copy of this key sequence object without each of the given keys (taken from the left). """
        if self.startswith(keys):
            return LexerKeys(self[len(keys):])
        s = _remove_chars(self, keys)
        return LexerKeys(s)

    def without_star(self) -> T:
        """ Return a copy of this key sequence without the first asterisk. """
        return self.without(KEY_STAR)

    def is_star(self, index=None) -> bool:
        """ If no arguments, is the current key set only an asterisk?
            With one argument, is the key at the given index an asterisk? """
        return (self if index is None else self[index]) == KEY_STAR

    @classmethod
    def cleanse_from_rtfcre(cls, s:str) -> T:
        """ Lexer input may come from the user, in which case the formatting cannot be trusted.
            Cleanse the string of abnormalities before parsing it as usual. """
        return cls.from_rtfcre(cls.map_strokes(s, _cleanse_stroke))


def _remove_chars(s:str, chars:Iterable[str]) -> str:
    """ Return a copy of <s> with each of the characters in <chars> removed, starting from the left. """
    return reduce(_remove_one, chars, s)


def _remove_one(s:str, c:str, replace=str.replace) -> str:
    """ Return a copy of <s> with the character <c> removed starting from the left. """
    return replace(s, c, "", 1)


def _cleanse_stroke(s:str) -> str:
    """ A vigorous formatting operation for RTFCRE strings close to user operation.
        Remove all characters that are considered invalid in steno strings for the parser.
        Translate any literal numbers by replacing them with their key equivalents and adding
        a number key to the beginning of the stroke if one or more was replaced."""
    rep = s.translate(TF_DICT)
    if rep != s and NUMBER_LITERALS_IN(s) and KEY_NUMBER not in s:
        return KEY_NUMBER + rep
    return rep
