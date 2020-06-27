""" Module for key-search dictionaries from generic to specialized. """

from bisect import bisect_left, insort_left
from itertools import islice
from operator import methodcaller
import re
from typing import Any, Callable, Dict, Iterable, List, Tuple, TypeVar

SKT = TypeVar("SKT")        # Similarity-transformed key (simkey) type.
KT = TypeVar("KT")          # Raw key type.
KeyPair = Tuple[SKT, KT]    # Sortable tuple type: (simkey, rawkey).
BisectList = List[KeyPair]  # Bisect-searchable list type with sorted tuples.
VT = TypeVar("VT")          # Value type.

Iterable_KT = Iterable[KT]
Iterable_SKT = Iterable[SKT]
PickleState = Tuple[Dict[KT, VT], Dict[str, Any]]


class SimilarKeyDict(Dict[KT, VT]):
    """
    A special hybrid dictionary implementation using a sorted key list along with the usual hash map. This allows
    lookups for keys that are "similar" to a given key in O(log n) time as well as exact O(1) hash lookups, at the
    cost of extra memory to store transformed keys and increased time for individual item insertion and deletion.
    It is most useful for large dictionaries that are mutated rarely after initialization, and which have a need
    to compare and sort their keys by some measure other than their natural sorting order.

    The "similarity function" returns a measure of how close two keys are to one another. This function should take a
    single key as input, and the return values should compare equal for keys that are deemed to be "similar". Even if
    they are not equal, keys with return values that are close will be close together in the list and may appear
    together in a search where equality is not required (subclasses must implement these searches). All implemented
    functionality other than similar key search is equivalent to that of a regular dictionary.

    Due to the dual nature of the data structure, there are additional restrictions on the data types allowed to be
    keys. As with a regular dict, keys must be of a type that is hashable, but they also must be totally orderable
    (i.e. it is possible to rank all the keys from least to greatest using comparisons) in order for sorting to work.
    Frozensets, for instance, would not work despite being hashable because they have no well-defined sorting order.
    The output type of the similarity function, if different, must be totally orderable as well.

    Inside the list, keys are stored in sorted order as tuples of (simkey, rawkey), which means they are ordered first
    by the value computed by the similarity function, and if those are equal, then by their natural value.

    The average-case time complexity for common operations are as follows:

    +-------------------+----------------+------+
    |     Operation     | SimilarKeyDict | dict |
    +-------------------+----------------+------+
    | Initialize        | O(n log n)     | O(n) |
    | Lookup (exact)    | O(1)           | O(1) |
    | Lookup (inexact)  | O(log n)       | O(n) |
    | Insert Item       | O(n)           | O(1) |
    | Delete Item       | O(n)           | O(1) |
    | Iteration         | O(n)           | O(n) |
    +-------------------+----------------+------+
    """

    _list: BisectList  # Sorted list of tuples: the similarity function output paired with the original key.

    def __init__(self, *args, simfn:Callable=None, mapfn:Callable=None, **kwargs):
        """ Initialize the dict and list and set up the similarity and map functions if given. """
        super().__init__(*args, **kwargs)
        if simfn is not None:
            self._simfn = simfn
        if mapfn is not None:
            self._mapfn = mapfn
        self._build_list()

    @staticmethod
    def _simfn(k:KT) -> SKT:
        """ The similarity function maps raw keys that share some property to the same "simkey".
            This will usually be overridden in __init__. If not, it maps keys to themselves. """
        return k

    def _mapfn(self, keys:Iterable_KT) -> Iterable_SKT:
        """ Optional mapped implementation of the similarity function for faster initialization.
            The default implementation is a straight call to map(). This is usually good enough. """
        return map(self._simfn, keys)

    def _build_list(self) -> None:
        """ Build (or rebuild) the sorted tuples list using the map function and the contents of the dict. """
        self._list = sorted(zip(self._mapfn(self), self))

    def _index_left(self, sk:SKT) -> int:
        """ Find the leftmost list index of <sk> (or the place it *would* be) using bisection search. """
        # Out of all tuples with an equal first value, the 1-tuple with this value compares less than any 2-tuple.
        return bisect_left(self._list, (sk,))

    def _index_exact(self, k:KT) -> int:
        """ Find the exact list index of the key <k> using bisection search (if it exists). """
        sk = self._simfn(k)
        return bisect_left(self._list, (sk, k))

    def _list_insert(self, k:KT) -> None:
        """ Find where <k> should go in the list and insert it. """
        sk = self._simfn(k)
        insort_left(self._list, (sk, k))

    def _list_remove(self, k:KT) -> None:
        """ Find where <k> is in the list and remove it. """
        idx = self._index_exact(k)
        del self._list[idx]

    def __setitem__(self, k:KT, v:VT) -> None:
        """ Set an item in the dict. If the key didn't exist before, insert it in the list. """
        if k not in self:
            self._list_insert(k)
        super().__setitem__(k, v)

    def pop(self, k:KT, *default:VT) -> VT:
        """ Remove an item from the dict and list and return its value, or <default> if not found. """
        if k in self:
            self._list_remove(k)
        return super().pop(k, *default)

    def __delitem__(self, k:KT) -> None:
        """ Just call pop() and throw away the return value. This will not affect sort order. """
        self.pop(k)

    def popitem(self) -> Tuple[KT, VT]:
        """ Remove the last (key, value) pair as found in the list and return it. The dict must not be empty. """
        if not self:
            raise KeyError('dictionary is empty')
        sk, k = self._list[-1]
        return k, self.pop(k)

    def setdefault(self, k:KT, default:VT=None) -> VT:
        """ Get an item from the dictionary. If it isn't there, set it to <default> and return it. """
        if k in self:
            return self[k]
        self[k] = default
        return default

    def clear(self) -> None:
        super().clear()
        self._list.clear()

    def update(self, *args, **kwargs) -> None:
        """ Update the dict and list using items from the given arguments. Because this is typically used
            to fill dictionaries with large amounts of items, a fast path is included if this one is empty. """
        if not self:
            super().update(*args, **kwargs)
            self._build_list()
        else:
            for (k, v) in dict(*args, **kwargs).items():
                self[k] = v

    def __reduce__(self) -> Tuple[type, tuple, PickleState]:
        """ Dict subclasses call __setitem__ to unpickle, which will happen before the key list exists in our case.
            We must sidestep this and unpickle everything using __setstate__ instead.  """
        state = (dict(self), self.__dict__)
        return self.__class__, (), state

    def __setstate__(self, state:PickleState) -> None:
        """ Unpickle both the items and the attributes. """
        d, attrs = state
        super().update(d)
        self.__dict__.update(attrs)

    def copy(self) -> "SimilarKeyDict":
        """ Make a shallow copy of the dict. The list will simply be reconstructed in the new copy. """
        return self.__class__(self, simfn=self._simfn, mapfn=self._mapfn)

    @classmethod
    def fromkeys(cls, seq:Iterable_KT, value:VT=None, **kwargs) -> "SimilarKeyDict":
        """ Make a new dict from a collection of keys, setting the value of each to <value>.
            Similarity functions can still be set by including them as keyword arguments after <value>. """
        d = dict.fromkeys(seq, value)
        return cls(d, **kwargs)

    def get_similar_keys(self, k:KT, count:int=None) -> List[KT]:
        """ Return a list of at most <count> keys that compare equal to <k> under the similarity function. """
        sk_start = self._simfn(k)
        idx_start = self._index_left(sk_start)
        idx_end = len(self)
        if count is not None:
            idx_end = min(idx_end, idx_start + count)
        keys = []
        items = self._list
        for idx in range(idx_start, idx_end):
            (sk, rk) = items[idx]
            if sk != sk_start:
                break
            keys.append(rk)
        return keys

    def get_nearby_keys(self, k:KT, count:int) -> List[KT]:
        """ Return a list of at most <count> keys that are equal or close to <k> under the similarity function.
            All keys will be approximately centered around <k> unless we're too close to one edge of the list. """
        idx_center = self._index_exact(k)
        idx_start = idx_center - count // 2
        if idx_start <= 0:
            items = self._list[:count]
        else:
            idx_end = idx_start + count
            if idx_end >= len(self):
                items = self._list[-count:]
            else:
                items = self._list[idx_start:idx_end]
        return [item[1] for item in items]


class RegexError(Exception):
    """ Raised if there's a syntax error in a regex search. """


def _regex_matcher(pattern:str) -> Callable:
    """ Compile a regular expression pattern and return a match predicate function. """
    try:
        return re.compile(pattern).match
    except re.error as e:
        raise RegexError(pattern + " is not a valid regular expression.") from e


class StringSearchDict(SimilarKeyDict[str, VT]):
    """
    A similar-key dictionary with special search methods for string keys.
    In order for the standard optimizations involving literal prefixes to work, the similarity function must
    not change the relative order of characters (i.e. changing case is fine, reversing the string is not.)
    """

    # Regex matcher for ASCII characters without special regex behavior when used at the start of a pattern.
    # Will always return at least the empty string (which is a prefix of everything).
    _LITERAL_PREFIX_MATCH = _regex_matcher(r'[\w \"#%\',\-:;<=>@`~]*')

    def prefix_match_keys(self, prefix:str, count:int=None) -> List[str]:
        """ Return a list of keys where the simkey starts with <prefix>, up to <count>. """
        sk_start = self._simfn(prefix)
        if not sk_start:
            # If the prefix is empty after transformation, it could possibly match anything.
            items = self._list if count is None else self._list[:count]
        else:
            # All matches will be found in the sort order between the prefix itself (inclusive) and
            # the prefix with one added to the ordinal of its final character (exclusive).
            sk_end = sk_start[:-1] + chr(ord(sk_start[-1]) + 1)
            idx_start = self._index_left(sk_start)
            idx_end = self._index_left(sk_end)
            if count is not None:
                idx_end = min(idx_end, idx_start + count)
            items = self._list[idx_start:idx_end]
        return [item[1] for item in items]

    def regex_match_keys(self, pattern:str, count:int=None) -> List[str]:
        """ Return a list of at most <count> keys that match the regex <pattern> from the start. """
        # First, figure out how much of the pattern string from the start is literal (no regex special characters).
        literal_prefix = self._LITERAL_PREFIX_MATCH(pattern).group()
        # If all matches must start with a certain literal prefix, we can narrow the range of our search.
        keys = self.prefix_match_keys(literal_prefix, count=None)
        if not keys:
            return []
        # If the prefix and pattern are equal, we have a complete literal string. Regex is not necessary.
        # Just do an *exact* prefix match in that case. Otherwise, compile the regular expression.
        if literal_prefix == pattern:
            match_op = methodcaller("startswith", pattern)
        else:
            match_op = _regex_matcher(pattern)
        # Run the match filter until <count> entries have been produced (if None, search the entire key list).
        return list(islice(filter(match_op, keys), count))
