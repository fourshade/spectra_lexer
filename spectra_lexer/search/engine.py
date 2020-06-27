from collections import defaultdict
from typing import Dict, Mapping, Tuple

from .string import RegexError, StringKeyMap, strip_case_map

StringMap = Mapping[str, str]
StringTuple = Tuple[str, ...]
StringSearchMap = StringKeyMap[StringTuple]   # Searchable one-to-many string mapping.
StringSearchResults = Dict[str, StringTuple]  # Dict of key strings mapped to tuples of matching value strings.


class StringSearchEngine:
    """ A hybrid forward+reverse string search engine.  """

    def __init__(self, *maps:StringSearchMap) -> None:
        self._maps = maps

    def search(self, pattern:str, count=None, *, reverse=False) -> StringSearchResults:
        """ Do a normal key string search for <pattern>.
            <count>   - Maximum number of matches returned. If None, there is no limit.
            <reverse> - If True, search for values instead of keys. """
        d = self._maps[reverse]
        keys = d.prefix_match_keys(pattern, count)
        return d.lookup(keys)

    def search_regex(self, pattern:str, count=None, *, reverse=False) -> StringSearchResults:
        """ Do a regular expression search for <pattern>. Return a special result if there's a regex syntax error.
            <count>   - Maximum number of matches returned. If None, there is no limit.
            <reverse> - If True, search for values instead of keys. """
        d = self._maps[reverse]
        try:
            keys = d.regex_match_keys(pattern, count)
        except RegexError:
            return {"INVALID REGEX": ()}
        return d.lookup(keys)

    def search_nearby(self, pattern:str, count:int, *, reverse=False) -> StringSearchResults:
        """ Search for key strings close to <pattern>.
            <count>   - Maximum number of matches returned.
            <reverse> - If True, search for values instead of keys. """
        d = self._maps[reverse]
        keys = d.get_nearby_keys(pattern, count)
        return d.lookup(keys)


class StringSearchFactory:

    def __init__(self, strip_chars=" ") -> None:
        self._strip_chars = strip_chars  # Characters to ignore at the ends of strings during search.

    def _build_map(self, *args) -> StringKeyMap:
        """ Build a new string search map that strips characters and removes case. """
        return strip_case_map(*args, strip=self._strip_chars)

    def _build_forward(self, s_map:StringMap) -> StringSearchMap:
        """ Create a tuple-based forward search map from a string mapping.
            zip() with one argument just packs each value into a 1-tuple. """
        items_iter = zip(s_map, zip(s_map.values()))
        return self._build_map(items_iter)

    def _build_reverse(self, s_map:StringMap) -> StringSearchMap:
        """ Create a tuple-based reverse search map from a string mapping. """
        rd = defaultdict(tuple)
        for k, v in s_map.items():
            rd[v] += (k,)
        return self._build_map(rd)

    def build(self, s_map:StringMap) -> StringSearchEngine:
        """ Build a bidirectional string search engine. """
        forward = self._build_forward(s_map)
        reverse = self._build_reverse(s_map)
        return StringSearchEngine(forward, reverse)
