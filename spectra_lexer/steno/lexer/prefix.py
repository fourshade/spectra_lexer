from typing import Callable, Sequence, Tuple


class PrefixTree:
    """ A trie-based structure with sequence-based keys that has the distinct advantage of
        quickly returning all values that match a given key or any of its prefixes, in order.
        It also allows duplicate keys, returning a list of all values that match it. """

    _root: dict  # Root node of the tree. Matches the empty sequence, which is a prefix of everything.

    def __init__(self):
        self._root = {"values": []}

    def __setitem__(self, k:Sequence, v:object) -> None:
        """ Add a new value to the list under the given key. If it doesn't exist, create nodes until you reach it. """
        node = self._root
        for element in k:
            node = node.get(element) or node.setdefault(element, {"values": []})
        node["values"].append(v)

    def __getitem__(self, k:Sequence) -> list:
        """ From a given sequence, return a list of all of the values that match
            any prefix of it in order from shortest prefix matched to longest. """
        node = self._root
        lst = node["values"][:]
        for element in k:
            if element not in node:
                break
            node = node[element]
            lst += node["values"]
        return lst


class CachingPrefixTree(dict, PrefixTree):
    """ Cache layer for the prefix tree. Rule matching is at the heart of the lexer and benefits greatly from caching.
        For multiprocessing to run, the cache must be pickleable. functools.lru_cache has problems with this.
        A dict subclass is very fast, but the tradeoff is that callers are on the honor system not to mutate it. """

    def __init__(self):
        super().__init__()
        PrefixTree.__init__(self)

    def __setitem__(self, k:Sequence, v:object, _tree_set=PrefixTree.__setitem__) -> None:
        """ Adding a value to the tree invalidates the cache. """
        if self:
            self.clear()
        _tree_set(self, k, v)

    def __missing__(self, k:Sequence, _tree_get=PrefixTree.__getitem__) -> list:
        """ Only compute matches from the tree on a cache miss. """
        v = _tree_get(self, k)
        super().__setitem__(k, v)
        return v


class PrefixFinder:
    """ Search engine that returns rules matching a prefix of ORDERED keys only. """

    _tree: CachingPrefixTree  # Primary search tree wrapped in a cache.
    _filtered_keys: Callable  # Callback to split keys into ordered and unordered sets.

    def __init__(self, unordered_filter:Callable[[str],Tuple[str,frozenset]]):
        """ Make the tree and memoize the filter that returns which keys will be and won't be tested in prefixes. """
        self._tree = CachingPrefixTree()
        self._filtered_keys = unordered_filter

    def add(self, skeys:str, letters:str, r:object) -> None:
        """ Separate the given set of keys into ordered and unordered keys,
            Index the rule itself and the unordered keys under the ordered keys (which contain any prefix). """
        ordered, unordered = self._filtered_keys(skeys)
        self._tree[ordered] = (r, letters, unordered)

    def find(self, skeys:str, letters:str) -> list:
        """ Return a list of all rules that match a prefix of the given ordered keys,
            a subset of the given letters, and a subset of the given unordered keys. """
        ordered, unordered = self._filtered_keys(skeys)
        return [r for (r, rl, ru) in self._tree[ordered] if rl in letters and ru <= unordered]
