""" Module for generic reverse dicts. """

from collections import defaultdict
from typing import Dict, List, TypeVar

KT = TypeVar("KT")    # Raw key type.
VT = TypeVar("VT")    # Value type.


class ReverseDict(Dict[VT, List[KT]]):
    """
    A reverse dictionary. Inverts a mapping from (key: value) to (value: [keys]).

    Since normal dictionaries can have multiple keys that map to the same value (many-to-one),
    reverse dictionaries must necessarily be some sort of one-to-many mapping.
    This means each entry must be a list. This class adds methods that manage those lists.

    Naming conventions are reversed - in a reverse dictionary, we look up a value to get a list
    of keys that would map to it in the forward dictionary.
    """

    def __init__(self, *args, match:dict=None, **kwargs):
        """ Create a matching inverse to the forward dict in the keyword argument <match> if given.
            Add items from other arguments normally to remain compatible with other dict constructors. """
        super().__init__(*args, **kwargs)
        if match is not None:
            self.match_forward(match)

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

    def match_forward(self, fdict:Dict[KT,VT]) -> None:
        """ Make this dict into the reverse of the given forward dict by rebuilding all of the lists.
            It is a fast way to populate a reverse dict from scratch after creation. """
        self.clear()
        rdict = defaultdict(list)
        list(map(list.append, [rdict[v] for v in fdict.values()], fdict))
        self.update(rdict)
