""" Module for generic key-search and reverse dicts. """

from bisect import bisect_left
from collections import defaultdict
from itertools import islice
from operator import methodcaller
import re
from typing import Callable, Dict, Iterable, Mapping, List, Tuple, TypeVar

# Regex to match ASCII characters without special regex behavior when used at the start of a pattern.
# Will always return at least the empty string (which is a prefix of everything).
REGEX_MATCH_LITERAL_PREFIX = re.compile(r'[\w \"#%\',\-:;<=>@`~]*').match

SKT = TypeVar("SKT")  # Similarity key type.
KT = TypeVar("KT")    # Key type.
VT = TypeVar("VT")    # Value type.


class SimilarKeyDict(Dict[KT, VT]):
    """
    A special hybrid dictionary implementation using a sorted key list along with the usual hash map. This allows
    lookups for keys that are "similar" to a given key in O(log n) time as well as exact O(1) hash lookups, at the
    cost of extra memory to store transformed keys and increased time for individual item insertion and deletion.
    It is most useful for large dictionaries that are mutated rarely after initialization, and which have a need
    to compare and sort their keys by some measure other than their natural sorting order (if they have one).

    The "similarity function" returns a measure of how close two keys are to one another. This function should take a
    single key as input, and the return values should compare equal for keys that are deemed to be "similar". Even if
    they are not equal, keys with return values that are close will be close together in the list and may appear
    together in a search where equality is not required (i.e filter_keys with no filter). All implemented
    functionality other than similarity search is equivalent to that of a regular dictionary.

    The keys must be of a type that is immutable, hashable, and totally orderable (i.e. it is possible to rank all
    the keys from least to greatest using comparisons) both before and after applying the given similarity function.
    Inside the list, keys are stored in sorted order as tuples of (simkey, rawkey), which means they are ordered first
    by the value computed by the similarity function, and if those are equal, then by their natural value.

    The average-case time complexity for common operations are as follows:

    +-------------------+-------------------+------+
    |     Operation     | SimilarSearchDict | dict |
    +-------------------+-------------------+------+
    | Initialize        | O(n log n)        | O(n) |
    | Lookup (exact)    | O(1)              | O(1) |
    | Lookup (inexact)  | O(log n)          | O(n) |
    | Insert Item       | O(n)              | O(1) |
    | Delete Item       | O(n)              | O(1) |
    | Iteration         | O(n)              | O(n) |
    +-------------------+-------------------+------+
    """

    _list: List[Tuple[SKT, KT]]  # Sorted list of tuples: the similarity function output paired with the original key.
    _simfn: Callable[[KT], KT]   # Similarity function, mapping one key to another of the same type.

    def __init__(self, *args, simfn:Callable[[KT],SKT]=lambda x: x, **kwargs):
        """ Initialize the dict and list to empty and set up the similarity function (identity if not provided).
            If other arguments were given, treat them as containing initial items to add as with dict.update(). """
        super().__init__()
        self._list = []
        self._simfn = simfn
        if args or kwargs:
            self.update(*args, **kwargs)

    def clear(self) -> None:
        super().clear()
        self._list.clear()

    def __setitem__(self, k:KT, v:VT) -> None:
        """ Set an item in the dict. If the key didn't exist before, find where it goes in the list and insert it. """
        if k not in self:
            idx = self._index_exact(k)
            self._list.insert(idx, (self._simfn(k), k))
        super().__setitem__(k, v)

    def __delitem__(self, k:KT) -> None:
        """ Delete an item from the dict and list. The key must exist. This will not affect sort order. """
        super().__delitem__(k)
        idx = self._index_exact(k)
        del self._list[idx]

    def update(self, *args, **kwargs) -> None:
        """ Update the dict and list using items from the given arguments. Because this is typically used
            to fill dictionaries with large amounts of items, a fast path is included if this one is empty. """
        if not self:
            super().update(*args, **kwargs)
            self._list = list(zip(map(self._simfn, self), self))
            self._list.sort()
        else:
            for (k, v) in dict(*args, **kwargs).items():
                self[k] = v

    def pop(self, k:KT, *default:VT) -> VT:
        """ Remove an item from the dict and list and return its value, or <default> if not found. """
        if k in self:
            idx = self._index_exact(k)
            del self._list[idx]
        if not default:
            return super().pop(k)
        return super().pop(k, *default)

    def popitem(self) -> Tuple[KT,VT]:
        """ Remove the last (key, value) pair as found in the list and return it. The dict must not be empty. """
        if not self:
            raise KeyError
        k = self._list.pop()[1]
        return k, super().pop(k)

    def setdefault(self, k:KT, default:VT=None) -> VT:
        """ Get an item from the dictionary. If it isn't there, set it to <default> and return it. """
        if k in self:
            return self[k]
        else:
            self[k] = default
            return default

    def copy(self) -> __qualname__:
        """ Make a shallow copy of the dict. The list will simply be reconstructed in the new copy. """
        return SimilarKeyDict(self, simfn=self._simfn)

    @staticmethod
    def fromkeys(seq:Iterable[KT], value:VT=None, *args, **kwargs) -> __qualname__:
        """ Make a new dict from a collection of keys, setting the value of each to <value>.
            simfn can still be set by including it as a keyword argument after <value>. """
        return SimilarKeyDict(dict.fromkeys(seq, value), **kwargs)

    def _index_left(self, simkey:SKT) -> int:
        """ Find the leftmost list index of <simkey> (or the place it *would* be) using bisection search. """
        # Out of all tuples with an equal first value, the 1-tuple with this value compares less than any 2-tuple.
        return bisect_left(self._list, (simkey,))

    def _index_exact(self, k:KT) -> int:
        """ Find the exact list index of the key <k> using bisection search (if it exists). """
        return bisect_left(self._list, (self._simfn(k), k))

    def get_similar_keys(self, k:KT, count:int=None) -> List[KT]:
        """ Return a list of at most <count> keys that compare equal to <k> under the similarity function. """
        _list = self._list
        simkey = self._simfn(k)
        idx_start = self._index_left(simkey)
        idx_end = len(_list)
        if count is not None:
            idx_end = min(idx_end, idx_start + count)
        keys = []
        for idx in range(idx_start, idx_end):
            (sk, rk) = _list[idx]
            if sk != simkey:
                break
            keys.append(rk)
        return keys


class StringSearchDict(SimilarKeyDict[str, VT]):
    """ A similar-key dictionary with special search methods for strings. """

    def prefix_match_keys(self, prefix:str, count:int=None) -> List[str]:
        """ Return a list producing all possible raw keys that could contain <prefix>, up to <count>. """
        sk_start = self._simfn(prefix)
        if not sk_start:
            # If the prefix is empty after transformation, it could possibly match anything.
            matches = self._list if count is None else self._list[:count]
        else:
            # All matches will be found in the sort order between the prefix itself (inclusive) and
            # the prefix with one added to the numerical value of its final character (exclusive).
            idx_start = self._index_left(sk_start)
            sk_end = sk_start[:-1] + chr(ord(sk_start[-1]) + 1)
            idx_end = self._index_left(sk_end)
            if count is not None:
                idx_end = min(idx_end, idx_start + count)
            matches = self._list[idx_start:idx_end]
        return [i[1] for i in matches]

    def regex_match_keys(self, pattern:str, count:int=None) -> List[str]:
        """ Return a list of at most <count> translations that match the regex <pattern> from the start. """
        # First, figure out how much of the pattern string from the start is literal (no regex special characters).
        literal_prefix = REGEX_MATCH_LITERAL_PREFIX(pattern).group()
        # If all matches must start with a certain literal prefix, we can narrow the range of our search.
        keys = self.prefix_match_keys(literal_prefix)
        if not keys:
            return []
        # If the prefix and pattern are equal, we have a complete literal string. Regex is not necessary.
        # Just do a raw (case-sensitive) prefix match in that case. Otherwise, compile the regular expression.
        if literal_prefix == pattern:
            match_op = methodcaller("startswith", pattern)
        else:
            match_op = re.compile(pattern).match
        # Run the match filter until <count> entries have been produced (if None, search the entire key list).
        return list(islice(filter(match_op, keys), count))


class ReverseDict(Dict[VT, List[KT]]):
    """
    A reverse dictionary. Inverts a mapping from (key: value) to (value: [keys]).

    Since normal dictionaries can have multiple keys that map to the same value (many-to-one),
    reverse dictionaries must necessarily be some sort of one-to-many mapping.
    This means each entry must be a list. This class adds methods that manage those lists.

    Naming conventions are reversed - in a reverse dictionary, we look up a value to get a list
    of keys that would map to it in the forward dictionary.
    """

    def append_key(self, v:VT, k:KT) -> None:
        """ Append the key <k> to the list located under the value <v>.
            Create a new list with that key if the value doesn't exist yet. """
        if v in self:
            self[v].append(k)
        else:
            self[v] = [k]

    def remove_key(self, v:VT, k:KT) -> None:
        """ Remove the key <k> from the list located under the value <v>. The key must exist.
            If it was the last key in the list, remove the dictionary entry entirely. """
        self[v].remove(k)
        if not self[v]:
            del self[v]

    def match_forward(self, fdict:Mapping[KT, VT]) -> None:
        """ Make this dict into the reverse of the given forward dict by rebuilding all of the lists.
            It is a fast way to populate a reverse dict from scratch after creation. """
        self.clear()
        rdict = defaultdict(list)
        list_append = list.append
        for (k, v) in fdict.items():
            list_append(rdict[v], k)
        self.update(rdict)
