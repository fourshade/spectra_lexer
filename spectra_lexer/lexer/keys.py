from functools import reduce
from typing import Iterable, TypeVar

from spectra_lexer.keys import StenoKeys

# Steno order is not enforced for any keys in this set. This has a large performance and accuracy cost.
# Only the asterisk is used in such a way that this treatment is worth it.
KEY_STAR = "*"
_UNORDERED_KEYS = frozenset({KEY_STAR})
_UNORDERED_KEYS_IN = _UNORDERED_KEYS.intersection


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
        super().__init__()
        if not _UNORDERED_KEYS_IN(keys):
            self.ordered = keys
        else:
            self.unordered = _UNORDERED_KEYS_IN(self.get_stroke(0))
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


def _remove_chars(s:str, chars:Iterable[str]) -> str:
    """ Return a copy of <s> with each of the characters in <chars> removed, starting from the left. """
    return reduce(_remove_one, chars, s)


def _remove_one(s:str, c:str, replace=str.replace) -> str:
    """ Return a copy of <s> with the character <c> removed starting from the left. """
    return replace(s, c, "", 1)
