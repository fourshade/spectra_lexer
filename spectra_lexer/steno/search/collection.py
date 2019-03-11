from operator import attrgetter
from typing import Dict, List, Optional

from .nexus import IndexNexus, ResourceNexus, RulesNexus, TranslationNexus
from .special import StenoSearchDict


def _new_dicts(tp:type):
    """ Create a function to load a new dict of a given type and re-sort them by priority. """
    def make_and_sort(self, d:dict):
        self._dicts[tp] = tp(d)
        values = sorted(self._dicts.values(), key=attrgetter("PRIORITY"), reverse=True)
        self._dicts = dict(zip(map(type, values), values))
        return bool(d)
    return make_and_sort


class MasterSearchDictionary:
    """ Class for similar-key string lookups on one of many dictionaries grouped into resource types. """

    _dicts: Dict[type, ResourceNexus]  # Current collection of resource dict distributors.
    _d: StenoSearchDict                # Current dict used for lookups.
    _last_match: str = ""              # Last search match selected by the user in the list.
    _mode_strokes: bool = False        # If True, search for strokes instead of translations.
    _mode_regex: bool = False          # If True, perform search using regex characters.

    def __init__(self):
        """ Create an empty collection and set the current dict to a default empty one. """
        self._dicts = {}
        self._d = ResourceNexus()

    set_index = _new_dicts(IndexNexus)
    set_rules = _new_dicts(RulesNexus)
    set_translations = _new_dicts(TranslationNexus)

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
        for test_d in self._dicts.values():
            result = test_d.check(pattern, strokes=self._mode_strokes)
            if result is not None:
                d, pattern = result
                self._d = d
                return d.search(pattern, count, self._mode_regex)
        return []

    def lookup(self, match:str) -> Optional[list]:
        """ Look up mappings from a match found in the current dict, unless the match is not new. """
        if self._last_match != match:
            self._last_match = match
            return self._d.get_list(match)

    def get_query(self, mapping:object) -> tuple:
        """ Make a lexer query based on the current dict type, the last match, and this mapping. """
        return self._d.command(self._last_match, mapping)
