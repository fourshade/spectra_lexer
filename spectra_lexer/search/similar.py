""" Module for key-search dictionaries from generic to specialized. """

from bisect import bisect_left, insort_left
from typing import Callable, Dict, Iterable, List, MutableMapping, TypeVar

SK = TypeVar("SK")  # Similarity-transformed key (simkey) type.
K = TypeVar("K")    # Raw key type.
V = TypeVar("V")    # Value type.
Iterable_K = Iterable[K]
Iterable_SK = Iterable[SK]
List_K = List[K]
Dict_KV = Dict[K, V]
SimFunc = Callable[[K], SK]
MapFunc = Callable[[Iterable_K], Iterable_SK]


class SimilarKeyMap(MutableMapping[K, V]):
    """
    A special hybrid mapping implementation using a sorted key list along with a normal dictionary. This allows
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
    keys. As with dictionaries, keys must be of a type that is hashable, but they also must be totally orderable
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

    def __init__(self, *args, simfn:SimFunc=None, mapfn:MapFunc=None):
        """ Initialize the dict and list and set up the similarity and map functions if given. """
        self._d = {}      # Standard dictionary. Used for all mapping operations.
        self._list = []   # Sorted list of tuples: the similarity function output paired with the original key.
        if simfn is not None:
            self._simfn = simfn
        if mapfn is not None:
            self._mapfn = mapfn
        if args:
            self._d.update(*args)
            self._rebuild_list()

    @staticmethod
    def _simfn(k:K) -> SK:
        """ The similarity function maps raw keys that share some property to the same "simkey".
            This will usually be overridden in __init__. If not, it maps keys to themselves. """
        return k

    def _mapfn(self, keys:Iterable_K) -> Iterable_SK:
        """ Optional mapped implementation of the similarity function for faster initialization.
            The default implementation is a straight call to map(). This is usually good enough. """
        return map(self._simfn, keys)

    def _rebuild_list(self) -> None:
        """ Rebuild the sorted tuples list using the map function and the contents of the dict. """
        self._list = sorted(zip(self._mapfn(self._d), self._d))

    def _index_left(self, sk:SK) -> int:
        """ Find the leftmost list index of <sk> (or the place it *would* be) using bisection search. """
        # Out of all tuples with an equal first value, the 1-tuple with this value compares less than any 2-tuple.
        return bisect_left(self._list, (sk,))

    def _index_exact(self, k:K) -> int:
        """ Find the exact list index of the key <k> using bisection search (if it exists). """
        sk = self._simfn(k)
        return bisect_left(self._list, (sk, k))

    def _list_insert(self, k:K) -> None:
        """ Find where <k> should go in the list and insert it. """
        sk = self._simfn(k)
        insort_left(self._list, (sk, k))

    def _list_remove(self, k:K) -> None:
        """ Find where <k> is in the list and remove it. """
        idx = self._index_exact(k)
        del self._list[idx]

    def __len__(self) -> int:
        return len(self._d)

    def __iter__(self) -> Iterable_K:
        return iter(self._d)

    def __getitem__(self, k:K) -> V:
        return self._d[k]

    def __setitem__(self, k:K, v:V) -> None:
        """ Set an item in the dict. If the key didn't exist before, insert it in the list. """
        if k not in self._d:
            self._list_insert(k)
        self._d[k] = v

    def __delitem__(self, k:K) -> None:
        """ Remove an item from the dict and list. This will not affect sort order. """
        del self._d[k]
        self._list_remove(k)

    def get_similar_keys(self, k:K, count:int=None) -> List_K:
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

    def get_nearby_keys(self, k:K, count:int) -> List_K:
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

    def lookup(self, keys:Iterable_K) -> Dict_KV:
        """ Look up every key in <keys> and return all items in a dictionary. All of the keys must exist.
            ABC subclasses are hit rather hard by method call overhead; this helps speed things up. """
        d = self._d
        return {k: d[k] for k in keys}
