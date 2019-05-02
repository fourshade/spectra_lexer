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

    def compile(self) -> None:
        self._compile(self._root, [])

    def _compile(self, node:dict, values:list) -> None:
        """ Finalize the tree by populating nodes with values from all possible prefixes. """
        v = node.pop("values")
        v += values
        for n in node.values():
            self._compile(n, v)
        node["values"] = v

    def __getitem__(self, k:Sequence) -> list:
        """ From a given sequence, return a list of all of the values that match
            any prefix of it in order from shortest prefix matched to longest. """
        node = self._root
        for element in k:
            if element not in node:
                break
            node = node[element]
        return node["values"]


class PrefixFinder:
    """ Search engine that finds rules matching a prefix of ORDERED keys only. """

    _tree: PrefixTree         # Primary search tree.
    _filtered_keys: Callable  # Callback to split keys into ordered and unordered sets.

    def __init__(self, items:Sequence[Tuple[str,str,object]], unordered_filter:Callable[[str],Tuple[str,frozenset]]):
        """ Make the tree and the filter that returns which keys will be and won't be tested in prefixes.
            Separate the given sets of keys into ordered keys (which contain any prefix) and unordered keys.
            Index the rules, letters, and unordered keys under the ordered keys and compile the tree. """
        tree = self._tree = PrefixTree()
        self._filtered_keys = unordered_filter
        for (skeys, letters, r) in items:
            ordered, unordered = self._filtered_keys(skeys)
            tree[ordered] = (r, letters, unordered)
        tree.compile()

    def __call__(self, skeys:str, letters:str) -> list:
        """ Return a list of all rules that match a prefix of the given ordered keys,
            a subset of the given letters, and a subset of the given unordered keys. """
        ordered, unordered = self._filtered_keys(skeys)
        return [r for (r, rl, ru) in self._tree[ordered] if rl in letters and ru <= unordered]
