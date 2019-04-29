from typing import List

from .nexus import ResourceNexus
from spectra_lexer.types import delegate_to


class SearchDictionary:
    """ Master class for similar-key string lookups on one of many dictionaries grouped into resource types. """

    _collection: List[ResourceNexus]  # Current collection of nexus objects, limited to one of each type.
    _nexus: ResourceNexus             # Current nexus used for searches and basic lookups.

    def __init__(self):
        """ Create a collection with a single fallback nexus (to ensure that searches always return *something*). """
        self._collection = [ResourceNexus()]

    def new(self, r_key:str, d:dict) -> None:
        """ Make a new nexus, overwrite the previous one of the same type (if any), and re-sort them by priority. """
        self._collection.append(ResourceNexus.from_resource(r_key, d))
        self._collection = sorted({type(n): n for n in self._collection}.values(), reverse=True)

    def search(self, pattern:str, count:int, *, strokes:bool=False, **search_kwargs) -> List[str]:
        """ Check which, if any, of our current nexus objects accepts this input pattern and mode.
            Search for the modified pattern in the first nexus we find and return a list of results. """
        for nexus in self._collection:
            new_pattern = nexus.check(pattern, strokes=strokes)
            if new_pattern is not None:
                self._nexus = nexus
                return nexus.search(new_pattern, count, **search_kwargs)

    lookup = delegate_to("_nexus")
    command_args = delegate_to("_nexus")
