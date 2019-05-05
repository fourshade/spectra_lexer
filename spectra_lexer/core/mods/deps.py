from collections import defaultdict, namedtuple
from typing import Dict, Iterable, List, Set


class _Dependency(namedtuple("dep", "key requires")):
    """ Custom class for a sortable dependency. """

    def __lt__(self, other) -> bool:
        """ One resource must be loaded before another if its key appears in the other's requirement set. """
        return self.key in other.requires


class DependencyOrderer:
    """ Custom class for sorting dependencies by string key. """

    _requirements: Dict[str, Set[str]]  # Dict {k: v} where every resource in set `v` must be loaded before `k`.

    def __init__(self):
        self._requirements = defaultdict(set)

    def add_requirements(self, provides:Iterable[str], requires:Set[str]) -> None:
        """ Add one or more resource keys that something <provides> and a set of keys that it <requires> first. """
        for k in provides:
            self._requirements[k] |= requires

    def sorted_keys(self) -> List[str]:
        """ Sort the requirement keys so that all dependencies are met in a valid order.
            Resources with no providers are ignored (they cannot be fulfilled anyway).
            Non-providers can have their resources fulfilled in any order. """
        deps = [_Dependency(*i) for i in self._requirements.items()]
        return [dp.key for dp in sorted(deps)]
