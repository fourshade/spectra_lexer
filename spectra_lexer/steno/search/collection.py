from typing import List

from .nexus import ResourceNexus
from spectra_lexer.utils import delegate_to


class MasterSearchDictionary:
    """ Class for similar-key string lookups on one of many dictionaries grouped into resource types. """

    _collection: List[ResourceNexus]  # Current collection of resource dict distributors.
    _nexus: ResourceNexus             # Current nexus used for searches and basic lookups.
    _mode_strokes: bool = False       # If True, search for strokes instead of translations.
    _mode_regex: bool = False         # If True, perform search using regex characters.

    def __init__(self):
        """ Create a collection with a single fallback nexus (to ensure it is never None). """
        self._nexus = ResourceNexus()
        self._collection = [self._nexus]

    def new_resource(self, ntype:type, d:dict) -> None:
        """ Make a new nexus, overwrite the previous one of the same type (if any), and re-sort them by priority. """
        self._collection = [n for n in self._collection if type(n) != ntype] + [ntype(d)]
        self._collection.sort(key=lambda n: n.PRIORITY, reverse=True)

    def set_mode_strokes(self, enabled:bool) -> None:
        """ Set strokes search mode on or off. """
        self._mode_strokes = enabled

    def set_mode_regex(self, enabled:bool) -> None:
        """ Set whether or not searches treat input queries as regular expressions. """
        self._mode_regex = enabled

    def search(self, pattern:str, count:int) -> List[str]:
        """ Check which, if any, of our current nexus objects accepts this input pattern.
            Search for the modified pattern in the first dict we get back and return a list of results. """
        for nexus in self._collection:
            new_pattern = nexus.check(pattern, strokes=self._mode_strokes)
            if new_pattern is not None:
                self._nexus = nexus
                return nexus.search(new_pattern, count, self._mode_regex)

    lookup = delegate_to("_nexus")
    command_args = delegate_to("_nexus")
