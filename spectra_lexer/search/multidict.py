""" Contains functions for creating multi-valued dictionaries from normal ones.
    Values are stored in tuples to protect against accidental in-place mutation. """

from collections import defaultdict
from typing import Dict, Mapping, Tuple, TypeVar

K = TypeVar("K")
V = TypeVar("V")
Mapping_KV = Mapping[K, V]             # Ordinary mapping. To reverse it, the values must also be hashable.
MultiDict_KV = Dict[K, Tuple[V, ...]]  # Multidict of keys mapped to tuples of matching values.
MultiDict_VK = Dict[V, Tuple[K, ...]]  # Multidict of values mapped to tuples of matching keys.


def forward_multidict(mapping:Mapping_KV) -> MultiDict_KV:
    """ Convert a mapping to a tuple-based multidict. 'forward' means the mapping direction is unchanged.
        This means each key will only have one value. zip() with one argument packs each value into a 1-tuple. """
    return dict(zip(mapping, zip(mapping.values())))


def reverse_multidict(mapping:Mapping_KV) -> MultiDict_VK:
    """ Convert a mapping to a tuple-based multidict where the mapping direction is reversed.
        Multiple keys may map to the same value, so a multidict is necessary to do this right. """
    rd = defaultdict(tuple)
    for k, v in mapping.items():
        rd[v] += (k,)
    return rd
