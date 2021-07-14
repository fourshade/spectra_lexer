""" Module for similar-key search operations, further specialized to string keys. """

from bisect import bisect_left, insort_left
from itertools import islice, repeat
from operator import itemgetter, methodcaller
import random
import re
from typing import Callable, Generic, Iterable, List, TypeVar

K = TypeVar("K")    # Original key type.
SK = TypeVar("SK")  # Similarity-transformed key (simkey) type.
Iterable_K = Iterable[K]
Iterable_SK = Iterable[SK]
List_K = List[K]

K_ITEMGETTER = itemgetter(1)   # Extracts keys from item tuples.
SK_ITEMGETTER = itemgetter(0)  # Extracts simkeys from item tuples.


class SimilarKeyIndex(Generic[K, SK]):
    """
    Abstract search index using a sorted key list. This allows lookups for keys that are "similar" to a
    given key in O(log n) time, at the cost of extra memory to store transformed keys and increased time for
    individual item insertion and deletion as compared to a dictionary. It is most useful for large collections
    of orderable keys that are mutated rarely after initialization, and which need to be compared and sorted
    by some measure other than their natural sorting order.

    The "similarity function" returns a measure of how close two keys are to one another. This function should take a
    single key as input, and the return values should compare equal for keys that are deemed to be "similar". Even if
    they are not equal, keys with return values that are close will be close together in the list and may appear
    together in a search where equality is not required (subclasses may implement these searches).

    Due to the nature of the data structure, there are restrictions on the data types allowed to be keys.
    All keys must be totally orderable (i.e. it is possible to rank them from least to greatest using comparisons).
    The output type of the similarity function, if different, must be totally orderable as well.

    Inside the list, keys are stored in sorted order as tuples of (simkey, rawkey), which means they are ordered first
    by the value computed by the similarity function, and if those are equal, then by their natural value.

    The average-case time complexity for common operations are as follows:

    +-------------------+-----------------+------+
    |     Operation     | SimilarKeyIndex | dict |
    +-------------------+-----------------+------+
    | Initialize        | O(n log n)      | O(n) |
    | Lookup (exact)    | O(log n)        | O(1) |
    | Lookup (inexact)  | O(log n)        | O(n) |
    | Insert Item       | O(n)            | O(1) |
    | Delete Item       | O(n)            | O(1) |
    | Iteration         | O(n)            | O(n) |
    +-------------------+-----------------+------+
    """

    def __init__(self) -> None:
        self._list = []  # Sorted list of tuples: the similarity function output paired with the original key.

    def simfn(self, k:K) -> SK:
        """ The similarity function maps raw keys that share some property to the same "simkey". Must be overridden. """
        raise NotImplementedError

    def mapfn(self, keys:Iterable_K) -> Iterable_SK:
        """ Mapped implementation of the similarity function. May be overridden for faster initialization.
            The default implementation is a straight call to map(). This is usually good enough. """
        return map(self.simfn, keys)

    def _index_left(self, sk:SK) -> int:
        """ Find the leftmost list index of <sk> (or the place it *would* be) using bisection search. """
        # Out of all tuples with an equal first value, the 1-tuple with this value compares less than any 2-tuple.
        return bisect_left(self._list, (sk,))

    def _index_exact(self, k:K) -> int:
        """ Find the exact list index of the key <k> using bisection search (if it exists). """
        sk = self.simfn(k)
        return bisect_left(self._list, (sk, k))

    def insert(self, k:K) -> None:
        """ Find where <k> should go in the list and insert it. """
        sk = self.simfn(k)
        insort_left(self._list, (sk, k))

    def remove(self, k:K) -> None:
        """ Find where <k> is in the list and remove it. """
        idx = self._index_exact(k)
        del self._list[idx]

    def clear(self) -> None:
        self._list.clear()

    def update(self, keys:Iterable_K) -> None:
        """ Add all <keys> to the list at once using the map function and sort it. """
        keys = list(keys)
        self._list += zip(self.mapfn(keys), keys)
        self._list.sort()

    def _iter_keys(self, idx_start=0, count:int=None, *, getter=K_ITEMGETTER) -> Iterable_K:
        """ Return an iterator over keys starting at <idx_start> with an optional limit of <count>. """
        items = self._list
        if count is not None:
            idx_end = idx_start + count
            items = items[idx_start:idx_end]
        elif idx_start:
            items = items[idx_start:]
        return map(getter, items)

    def __len__(self) -> int:
        return len(self._list)

    def __iter__(self) -> Iterable_K:
        return self._iter_keys()

    def get_similar_keys(self, k:K, count:int=None) -> List_K:
        """ Return a list of at most <count> keys that compare equal to <k> under the similarity function. """
        sk_start = self.simfn(k)
        idx_start = self._index_left(sk_start)
        nkeys = 0
        for sk in self._iter_keys(idx_start, count, getter=SK_ITEMGETTER):
            if sk != sk_start:
                break
            nkeys += 1
        return list(self._iter_keys(idx_start, nkeys))

    def get_nearby_keys(self, k:K, count:int) -> List_K:
        """ Return a list of at most <count> keys that are equal or close to <k> under the similarity function.
            All keys will be approximately centered around <k> unless we're too close to one edge of the list. """
        idx_center = self._index_exact(k)
        idx_start = idx_center - count // 2
        max_start = len(self) - count
        if idx_start > max_start:
            idx_start = max_start
        if idx_start < 0:
            idx_start = 0
        return list(self._iter_keys(idx_start, count))

    def get_random_keys(self, count:int) -> List_K:
        """ Return a list of at most <count> unique random keys. """
        items = random.sample(self._list, min(count, len(self)))
        return list(map(K_ITEMGETTER, items))


StringIter = Iterable[str]
StringList = List[str]


class RegexError(Exception):
    """ Raised if there's a syntax error in a regex search. """


def _regex_matcher(pattern:str) -> Callable:
    """ Compile a regular expression pattern and return a match predicate function. """
    try:
        return re.compile(pattern).match
    except re.error as e:
        raise RegexError(pattern + " is not a valid regular expression.") from e


class StringKeyIndex(SimilarKeyIndex[str, str]):
    """ A similar-key index with special search methods for string keys.
        In order for the standard optimizations involving literal prefixes to work, the similarity function must
        not change the relative order of characters (i.e. changing case is fine, reversing the string is not.) """

    # Regex matcher for ASCII characters without special regex behavior when used at the start of a pattern.
    # Will always return at least the empty string (which is a prefix of everything).
    _LITERAL_PREFIX_MATCH = _regex_matcher(r'[\w \"#%\',\-:;<=>@`~]*')

    # Case-insensitive search is the most common use case.
    simfn = staticmethod(str.lower)

    def _iter_prefix_keys(self, prefix:str, count:int=None) -> StringIter:
        """ Return an iterator over possible matches for <prefix>, up an optional limit of <count>. """
        sk_start = self.simfn(prefix)
        if not sk_start:
            # If the prefix is empty after transformation, it could possibly match anything.
            idx_start = 0
        else:
            # All matches will be found in the sort order between the prefix itself (inclusive) and
            # the prefix with one added to the ordinal of its final character (exclusive).
            sk_end = sk_start[:-1] + chr(ord(sk_start[-1]) + 1)
            idx_start = self._index_left(sk_start)
            idx_end = self._index_left(sk_end)
            length = idx_end - idx_start
            count = length if count is None else min(count, length)
        return self._iter_keys(idx_start, count)

    def prefix_match_keys(self, prefix:str, count:int=None) -> StringList:
        """ Return a list of keys where the simkey starts with <prefix>, up an optional limit of <count>. """
        return list(self._iter_prefix_keys(prefix, count))

    def regex_match_keys(self, pattern:str, count:int=None) -> StringList:
        """ Return a list of at most <count> keys that match the regex <pattern> from the start. """
        # First, figure out how much of the pattern string from the start is literal (no regex special characters).
        # If all matches must start with a literal prefix, we can narrow the range of our search.
        literal_prefix = self._LITERAL_PREFIX_MATCH(pattern).group()
        # If the prefix and pattern are equal, we have a complete literal string. Regex is not necessary.
        # Just do an *exact* prefix match in that case. Otherwise, compile the regular expression.
        if literal_prefix == pattern:
            match_op = methodcaller("startswith", pattern)
        else:
            match_op = _regex_matcher(pattern)
        # Run the match filter until <count> entries have been produced (if None, search the entire key list).
        keys = self._iter_prefix_keys(literal_prefix)
        return list(islice(filter(match_op, keys), count))


class StripCaseIndex(StringKeyIndex):
    """ String index with similarity functions that ignore case and/or certain ending characters. """

    def __init__(self, strip_chars=" ") -> None:
        super().__init__()
        self._strip_chars = strip_chars  # Characters to ignore at the ends of strings during search.

    def simfn(self, s:str) -> str:
        """ Similarity function that removes case and strips a user-defined set of characters. """
        return s.strip(self._strip_chars).lower()

    def mapfn(self, s_iter:StringIter) -> StringIter:
        """ Mapping the built-in string methods separately provides a good speed boost for large dictionaries. """
        return map(str.lower, map(str.strip, s_iter, repeat(self._strip_chars)))
