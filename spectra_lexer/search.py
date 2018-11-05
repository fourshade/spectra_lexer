from bisect import bisect_left
import collections
import itertools
import operator
import re
from typing import Callable, List, Mapping

# Regex to match ASCII characters matched as literals counting from the start of a regex pattern.
REGEX_MATCH_PREFIX = re.compile(r'[\w \"#%\',\-:;<=>@`~]+').match


class SimilarSearchDict(dict):
    """
    A special dictionary implementation using a sorted key list along with the usual hash map. This allows lookups
    for keys that are "similar" to a given key in O(log n) time as well as exact O(1) hash lookups, at the cost of
    extra memory to store transformed keys and increasing item insertion and deletion to average between O(log n)
    and O(n) amortized time (depending on how often new items are added between searches). No penalty is incurred
    for changing the values of existing items. The worst case is when item insertions and deletions/searches are
    done alternately. It is most useful for dictionaries whose items are inserted/deleted rarely, and which have
    a need to compare and sort their keys by some measure other than their natural sorting order (if they have one).

    The "similarity function" returns a measure of how close two keys are to one another. This function should take a
    single key as input, and the return values should compare equal for keys that are deemed to be "similar". Even if
    they are not equal, keys with return values that are close will be close together in the list and may appear
    together in a search where equality is not required (i.e get_similar with count defined). All implemented
    functionality other than similarity search is equivalent to that of a regular dictionary.

    The keys must be of a type that is immutable, hashable, and totally orderable (i.e. it is possible to rank all the
    keys from least to greatest using comparisons) both before and after applying the given similarity function.

    Inside the list, keys are stored in sorted order as tuples of (simkey, rawkey), which means they are ordered first
    by the value computed by the similarity function, and if those are equal, then by their natural value.
    """

    def __init__(self, simfn=None, *args, **kwargs):
        """ Initialize the dict and list to empty, and set the sort flag.
            The first argument sets the similarity function. It is the identity function if None or not provided.
            If other arguments were given, treat them as sets of initial items to add as with dict.update(). """
        super().__init__()
        self._list = []
        self._needs_sorting = False
        if simfn is not None:
            self._simfn = simfn
        else:
            self._simfn = lambda x: x
        if args or kwargs:
            self.update(*args, **kwargs)

    def clear(self):
        super().clear()
        self._list.clear()

    def __setitem__(self, k, v):
        """ Set an item in the dict. If the key didn't exist before, add it to the list and set the sort flag. """
        if k not in self:
            self._list.append((self._simfn(k), k))
            self._needs_sorting = True
        super().__setitem__(k, v)

    def __delitem__(self, k):
        """
        Delete an item in the dict+list (if it exists). Deleting an item will not affect the order of the list,
        but it has to be sorted in order to find the key using bisection. We could look for the key the slow way
        under O(n) time, but sorting the list is only O(n log n) or less and will need to be done anyway for
        searches or further deletions.
        """
        if k in self:
            super().__delitem__(k)
            if self._needs_sorting:
                self.sort()
            idx = bisect_left(self._list, (self._simfn(k), k))
            del self._list[idx]

    def update(self, *args, **kwargs):
        """ Update the dict using items from given arguments. Because this is typically used to fill dictionaries with
            large amounts of items, a fast path is included if ours is empty, and the list is immediately sorted. """
        if not self:
            super().update(*args, **kwargs)
            self._list = list(zip(map(self._simfn, self), self))
        else:
            for (k, v) in dict(*args, **kwargs).items():
                self[k] = v
        self.sort()

    def sort(self) -> None:
        """ Perform a sort on the list. Is done when necessary; can also be done manually during initialization. """
        self._list.sort()
        self._needs_sorting = False

    def _index_left(self, k) -> int:
        """ Sort the list if necessary, then find the leftmost index to the given key under the similarity function. """
        if self._needs_sorting:
            self.sort()
        # Out of all tuples with an equal first value, the 1-tuple with this value compares less than any 2-tuple.
        return bisect_left(self._list, (self._simfn(k),))

    def filter_keys(self, k, count:int=None, filterfn:Callable=None):
        """ Filter the list of keys starting from the position where k is/would be and return up to <count> matches,
            or all matches if count is None. The filter function is a T/F comparison between each list key and the
            given key after both have been altered by the similarity function; if None, all keys are returned. """
        _list = self._list
        simkey = self._simfn(k)
        idx = self._index_left(k)
        keys = []
        while idx < len(_list):
            (sk, rk) = _list[idx]
            if filterfn is not None and not filterfn(sk, simkey):
                break
            keys.append(rk)
            if count is not None and len(keys) >= count:
                break
            idx += 1
        return keys

    def get_similar_keys(self, k, count:int=None):
        """ Get a list of similar keys to the given key (they compare equal under the similarity function). """
        return self.filter_keys(k, count=count, filterfn=operator.eq)

    # Unimplemented methods from base class that are unsafe (can mutate the object).
    def setdefault(self, k, default=None): return NotImplementedError
    def pop(self, k): return NotImplementedError
    def popitem(self): return NotImplementedError


class ReverseStenoDict(SimilarSearchDict):
    """
    A reverse dictionary with search capabilities for steno translations.
    It has special searches and the similarity function defined.

    Since normal dictionaries can have multiple keys that map to the same value (many-to-one),
    reverse dictionaries must be able to store multiple values under the same key (one-to-many).
    This means that the lookup results must be lists. These methods manage those lists.

    Naming conventions are reversed - in a reverse dictionary, we look up a value
    to get a list of keys that would map to it in the forward dictionary.
    """

    def __init__(self, *args, **kwargs):
        """ Initialize the base dict with the search function and any given arguments. """
        def simfn(s:str, STRIP=str.strip, LOWER=str.lower):
            """ Translations are similar if they compare equal when stripped of case and certain exterior symbols. """
            return LOWER(STRIP(s, ' '))
        super().__init__(simfn=simfn, *args, **kwargs)

    def append_key(self, v:str, k) -> None:
        """ Append the given key to the list at the given value.
            Create a new list with that key if the value doesn't exist yet. """
        if v in self:
            self[v].append(k)
        else:
            self[v] = [k]

    def remove_key(self, v:str, k) -> None:
        """ Remove the given key from the list at the given value.
            If it was the last item in the list, remove the dictionary entry entirely. """
        if v in self:
            self[v].remove(k)
            if not self[v]:
                del self[v]

    def match_forward(self, fdict:Mapping) -> None:
        """ Update the dict to be the reverse of the given forward dict by rebuilding all the lists.
            It is a fast way to populate a reverse dict from scratch after creation. """
        self.clear()
        rdict = collections.defaultdict(list)
        list_append = list.append
        for (k, v) in fdict.items():
            list_append(rdict[v], k)
        self.update(rdict)

    def partial_match_keys(self, k:str, count:int=None) -> List[str]:
        """ Return a list of at most <count> keys that are equal to
            or begin with the given key under the similarity function. """
        return self.filter_keys(k, count=count, filterfn=str.startswith)

    def regex_match_keys(self, pattern:str, count:int=None) -> List[str]:
        """ Return a list of at most <count> translations that match the given regex pattern starting from index 0. """
        _list = self._list
        # First, figure out how much of the pattern string from the start is literal (no regex special characters).
        prefix_match = REGEX_MATCH_PREFIX(pattern)
        prefix = prefix_match.group() if prefix_match else ""
        # If we know that all matches start with a certain prefix, we can narrow the range of our search.
        # All possibilities will be found in the sort order between the prefix itself (inclusive) and
        # the prefix with one added to the numerical value of its final character (exclusive).
        marker_start = self._simfn(prefix)
        if not marker_start:
            # Prefix is empty after transformation - unfortunately this means we must search everything.
            search_start = 0
            search_end = len(_list)
        else:
            search_start = self._index_left(marker_start)
            marker_end = marker_start[:-1] + chr(ord(marker_start[-1])+1)
            search_end = self._index_left(marker_end)
            if search_start == search_end:
                # Range is empty - no possible matches.
                return []
        # Get the raw key values of every possibility from the list and set count to cover everything if it is None.
        keys = map(operator.itemgetter(1), _list[search_start:search_end])
        if count is None:
            count = search_end - search_start
        if prefix == pattern:
            # This is a complete literal string. Regex is not necessary; just do a partial case-sensitive match.
            return list(itertools.islice((k for k in keys if k.startswith(pattern)), count))
        # Attempt to match against the real value of the key over the entire possible range.
        rx_match = re.compile(pattern).match
        matches = []
        for k in filter(rx_match, keys):
            matches.append(k)
            if len(matches) >= count:
                break
        return matches
