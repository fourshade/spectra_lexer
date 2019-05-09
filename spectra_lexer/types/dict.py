""" Module for generic dict types with no other category. """

from collections import defaultdict
from typing import Iterable, Mapping


class multidict(dict):
    """ Implementation of a one-to-many mapping. It is a dict that may contain multiple values under one key.
        This means each entry must be a list. This class adds methods that manage those lists.
        All methods besides constructors are distinct from regular dict methods for compatibility. """

    def __init__(self, *args, **kwargs):
        super().__init__()
        if args or kwargs:
            self.update(*args, **kwargs)

    def copy(self):
        """ When copying the dict, use the right class. """
        return self.__class__(self)

    def add(self, k, v) -> None:
        """ Add the value <v> to the list located under the key <k>.
            Create a new list with that key if the value doesn't exist yet. """
        if k in self:
            self[k].append(v)
        else:
            self[k] = [v]

    def remove(self, k, v) -> None:
        """ Remove the value <v> from the list located under the key <k>. The key must exist.
            If it was the last key in the list, remove the dictionary entry entirely. """
        i = self[k]
        i.remove(v)
        if not i:
            del self[k]

    def update(self, *args:Iterable, **kwargs) -> None:
        """ Update the dict with any number of iterables, mappings, and/or keywords. """
        for src in (*args, kwargs):
            iterable = src.items() if isinstance(src, Mapping) else src
            if isinstance(src, multidict):
                for k, v in iterable:
                    self[k] += v
            else:
                for k, v in iterable:
                    self.add(k, v)

    def __iadd__(self, other:Iterable):
        self.update(other)
        return self

    def __missing__(self, k) -> list:
        """ Return an empty list on lookup failure. Do NOT add this list to the dict. """
        return []


class ReverseDict(dict):
    """ A reverse dictionary. Inverts a mapping from (key: value) to (value: [keys]). """

    def __init__(self, *args, _match:dict=None, **kwargs):
        """ Create a matching inverse to the forward dict in the keyword argument <_match> if given.
            Add items from other arguments normally to remain compatible with other dict constructors. """
        super().__init__(*args, **kwargs)
        if _match is not None:
            self.match_forward(_match)

    add = multidict.add
    remove = multidict.remove

    def match_forward(self, fdict:dict) -> None:
        """ Make this dict into the reverse of the given forward dict by rebuilding all of the lists.
            It is a fast way to populate a reverse dict from scratch after creation. """
        self.clear()
        rdict = defaultdict(list)
        list(map(list.append, [rdict[v] for v in fdict.values()], fdict))
        self.update(rdict)
