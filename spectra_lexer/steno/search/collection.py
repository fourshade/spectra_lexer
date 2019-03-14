from typing import List

from .nexus import IndexNexus, ResourceNexus, RulesNexus, TranslationNexus
from spectra_lexer.utils import delegate_to

# Maps resource key strings to the nexus types that use them.
_NEXUS_TABLE = {"index": IndexNexus,
                "rules": RulesNexus,
                "translations": TranslationNexus}


class NexusCollection:
    """ Contains many dictionaries grouped into resource types. """

    _nexus_list: List[ResourceNexus]  # Priority-ordered list of resource search objects.

    def __init__(self):
        """ Create a collection with a single fallback nexus (to ensure that searches always return *something*). """
        self._nexus_list = [ResourceNexus()]

    def new(self, r_key:str, d:dict) -> None:
        """ Make a new nexus, overwrite the previous one of the same type (if any), and re-sort them by priority. """
        ntype = _NEXUS_TABLE[r_key]
        self._nexus_list = [n for n in self._nexus_list if type(n) != ntype] + [ntype(d)]
        self._nexus_list.sort(key=lambda n: n.PRIORITY, reverse=True)

    __iter__ = delegate_to("_nexus_list")


class SearchDictionary:
    """ Master class for similar-key string lookups on one of many dictionaries grouped into resource types. """

    _collection: NexusCollection  # Current collection of nexus objects, limited to one of each type.
    _nexus: ResourceNexus         # Current nexus used for searches and basic lookups.

    def __init__(self):
        self._collection = NexusCollection()

    def search(self, pattern:str, count:int, strokes:bool=False, regex:bool=False) -> List[str]:
        """ Check which, if any, of our current nexus objects accepts this input pattern.
            Search for the modified pattern in the first dict we get back and return a list of results. """
        for nexus in self._collection:
            new_pattern = nexus.check(pattern, strokes=strokes)
            if new_pattern is not None:
                self._nexus = nexus
                return nexus.search(new_pattern, count, regex)

    new = delegate_to("_collection")

    lookup = delegate_to("_nexus")
    command_args = delegate_to("_nexus")
