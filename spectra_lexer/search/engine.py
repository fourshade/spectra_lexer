from collections import defaultdict
from itertools import repeat
from typing import Iterable, Mapping

from .string import MultiStringDict, MultiStringMap, RegexError, StringKeyMap, StringMap


class StringSearchEngine:
    """ A hybrid forward+reverse string search engine.  """

    def __init__(self, forward:StringMap, reverse:MultiStringMap) -> None:
        self._forward = forward
        self._reverse = reverse

    def _get_map(self, reverse:bool) -> StringKeyMap:
        return self._reverse if reverse else self._forward

    def search(self, pattern:str, count=None, *, reverse=False) -> MultiStringDict:
        """ Do a normal key string search for <pattern>.
            <count>   - Maximum number of matches returned. If None, there is no limit.
            <reverse> - If True, search for values instead of keys. """
        d = self._get_map(reverse)
        keys = d.prefix_match_keys(pattern, count)
        return d.lookup(keys)

    def search_regex(self, pattern:str, count=None, *, reverse=False) -> MultiStringDict:
        """ Do a regular expression search for <pattern>. Return a special result if there's a regex syntax error.
            <count>   - Maximum number of matches returned. If None, there is no limit.
            <reverse> - If True, search for values instead of keys. """
        d = self._get_map(reverse)
        try:
            keys = d.regex_match_keys(pattern, count)
        except RegexError:
            return {"INVALID REGEX": []}
        return d.lookup(keys)

    def search_nearby(self, pattern:str, count:int, *, reverse=False) -> MultiStringDict:
        """ Search for key strings close to <pattern>.
            <count>   - Maximum number of matches returned.
            <reverse> - If True, search for values instead of keys. """
        d = self._get_map(reverse)
        keys = d.get_nearby_keys(pattern, count)
        return d.lookup(keys)


class StringSearchFactory:

    def __init__(self, strip_chars=" ") -> None:
        self._strip_chars = strip_chars  # Characters to ignore at the ends of strings during search.

    def _simfn(self, s:str) -> str:
        """ Similarity function for search dicts that removes case and strips a user-defined set of symbols. """
        return s.strip(self._strip_chars).lower()

    def _simfn_mapped(self, s_iter:Iterable[str]) -> Iterable[str]:
        """ Mapping the built-in string methods separately provides a good speed boost for large dictionaries. """
        return map(str.lower, map(str.strip, s_iter, repeat(self._strip_chars)))

    def _kwargs(self) -> dict:
        """ Return keyword arguments with the similarity functions. """
        return dict(simfn=self._simfn, mapfn=self._simfn_mapped)

    def _build_forward(self, s_map:Mapping[str, str]) -> StringMap:
        """ Create a normal search dict from a string mapping. """
        return StringMap(s_map, **self._kwargs())

    def _build_reverse(self, s_map:Mapping[str, str]) -> MultiStringMap:
        """ This is the fastest way I could find to reverse a string mapping
            (even despite building and throwing away a giant list of None). """
        rd = defaultdict(list)
        list(map(list.append, [rd[v] for v in s_map.values()], s_map))
        return MultiStringMap(rd, **self._kwargs())

    def build(self, s_map:Mapping[str, str]) -> StringSearchEngine:
        """ Build a bidirectional string search engine. """
        forward = self._build_forward(s_map)
        reverse = self._build_reverse(s_map)
        return StringSearchEngine(forward, reverse)
