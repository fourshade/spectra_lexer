from operator import attrgetter
from typing import List, Optional

from .nexus import ResourceNexus


class MasterSearchDictionary:
    """ Class for similar-key string lookups on one of many dictionaries grouped into resource types. """

    _collection: List[ResourceNexus]  # Current collection of resource dict distributors.
    _nexus: ResourceNexus = None      # Current nexus used for searches and basic lookups.
    _last_match: str = ""             # Last search match selected by the user in the list.
    _mode_strokes: bool = False       # If True, search for strokes instead of translations.
    _mode_regex: bool = False         # If True, perform search using regex characters.

    def __init__(self):
        """ Create an empty collection. """
        self._collection = []

    def add_and_sort(self, nexus:ResourceNexus) -> None:
        """ Add a new dict nexus (or overwrite the previous one of the same type) and re-sort them by priority. """
        self._collection = [n for n in self._collection if type(n) != type(nexus)] + [nexus]
        self._collection.sort(key=attrgetter("PRIORITY"), reverse=True)

    def set_mode_strokes(self, enabled:bool) -> tuple:
        """ Set strokes search mode on or off. """
        self._mode_strokes = enabled
        return ()

    def set_mode_regex(self, enabled:bool) -> tuple:
        """ Set whether or not searches treat input queries as regular expressions. """
        self._mode_regex = enabled
        return ()

    def search(self, pattern, count) -> List[str]:
        """ Check which, if any, of our current nexus objects accepts this input pattern.
            Search for the modified pattern in the first dict we get back and return a list of results. """
        for nexus in self._collection:
            new_pattern = nexus.check(pattern, strokes=self._mode_strokes)
            if new_pattern is not None:
                self._nexus = nexus
                return nexus.search(new_pattern, count, self._mode_regex)
        return []

    def lookup(self, match:str) -> Optional[list]:
        """ Look up mappings from a match found in the current dict, unless the match is not new. """
        if self._last_match != match and self._nexus is not None:
            self._last_match = match
            return self._nexus.get_list(match)

    def get_command_args(self, mapping:object) -> Optional[tuple]:
        """ Get arguments for a command based on the current dict type, the last match, and this mapping. """
        if self._nexus is not None:
            return self._nexus.command(self._last_match, mapping)
