""" Module for steno-specific key-search dicts, including reverse and bidirectional dicts. """
from typing import Dict, TypeVar, Tuple

from spectra_lexer.search.key_search import StringSearchDict, ReverseDict

KT = TypeVar("KT")    # Key type.
VT = TypeVar("VT")    # Value type.


def strip_lower_simfn(strip_chars:str=' '):
    """ Create a similarity function that removes case and strips a user-defined set of symbols.
        This should work well for search with either ordering of strokes <-> translation. """
    # Define string methods as function closure locals for speed.
    strip = str.strip
    lower = str.lower
    def simfn(s:str) -> str:
        return lower(strip(s, strip_chars))
    return simfn


class StrokeSearchDict(StringSearchDict):
    """ String-based similar-key searchable dict for steno translations where key:value = strokes:translation. """


class TranslationSearchDict(StringSearchDict, ReverseDict):
    """ Reverse string-search dict that maps translations to lists of stroke sequences that will produce them. """


class BidirectionalStenoSearchDict(StrokeSearchDict):
    """ Composite steno dict class for ordinary lookups, reverse lookups, and special searches in both directions. """

    reverse: TranslationSearchDict  # Reverse search dict (translations -> strokes)

    def __init__(self, src_dict:Dict[KT,str]=None, **kwargs):
        """ Create both forward and reverse search dictionaries with specific characters stripped. """
        if src_dict is None:
            src_dict = {}
        # For stroke searches, hyphens should be stripped off the front (as well as spaces).
        super().__init__(src_dict, simfn=strip_lower_simfn(' -'), **kwargs)
        # For translation searches, just stripping spaces works well enough.
        self.reverse = TranslationSearchDict(src_dict, simfn=strip_lower_simfn(' '), **kwargs)
        self.prefix_match_strokes = self.prefix_match_keys
        self.regex_match_strokes = self.regex_match_keys
        self.prefix_match_translations = self.reverse.prefix_match_keys
        self.regex_match_translations = self.reverse.regex_match_keys

    def clear(self) -> None:
        super().clear()
        self.reverse.clear()

    def __setitem__(self, k:KT, v:VT) -> None:
        # If the key exists, we have to remove its old mapping from the reverse dictionary while we can still find it.
        if k in self:
            self.reverse.remove_key(self[k], k)
        super().__setitem__(k, v)
        self.reverse.append_key(v, k)

    def update(self, *args, **kwargs) -> None:
        """ Update the dictionary using a single iterable or mapping located in args. """
        if not self:
            # Fast path for when the dicts start out empty.
            super().update(*args, **kwargs)
            self.reverse.match_forward(self)
        else:
            # If items already exist, update dicts one item at a time to be safe.
            for (k, v) in dict(*args, **kwargs).items():
                self[k] = v

    def pop(self, k:KT, *default:VT) -> VT:
        """ Remove an item from the dict and list and return its value, or <default> if not found. """
        v = super().pop(k, *default)
        if v in self.reverse:
            if k in self.reverse[v]:
                self.reverse.remove_key(v, k)
        return v

    def __delitem__(self, k:KT) -> None:
        """ Just call pop() and throw away the return value. """
        self.pop(k)

    def popitem(self) -> Tuple[KT,VT]:
        """ Remove the last (key, value) pair as found in the list and return it. The dict must not be empty. """
        k, v = super().popitem()
        self.reverse.remove_key(v, k)
        return k, v

    def setdefault(self, k:KT, default:VT=None) -> VT:
        """ Get an item from the dictionary. If it isn't there, set it to <default> and return it. """
        if k in self:
            return self[k]
        self[k] = default
        return default

    def copy(self) -> __qualname__:
        """ Make a shallow copy of the composite dict using the forward data only. """
        return BidirectionalStenoSearchDict(self)
