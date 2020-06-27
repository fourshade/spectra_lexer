from collections import defaultdict
from itertools import repeat
from typing import Dict, Iterable, List, Mapping

from .dict import RegexError, StringSearchDict

MatchDict = Dict[str, List[str]]  # Dict matching key strings to lists of value strings.


class _SearchDict(StringSearchDict):

    def lookup(self, keys:Iterable[str]) -> MatchDict:
        raise NotImplementedError


class ForwardSearchDict(_SearchDict):

    def lookup(self, keys:Iterable[str]) -> MatchDict:
        """ Forward dict values are strings; wrap each one in a list. """
        return {k: [self[k]] for k in keys}


class ReverseSearchDict(_SearchDict):

    def lookup(self, keys:Iterable[str]) -> MatchDict:
        """ Reverse dict values are already lists; copy each one. """
        return {k: [*self[k]] for k in keys}


class StringSearchEngine:
    """ A hybrid forward+reverse string search engine.  """

    def __init__(self, forward:_SearchDict, reverse:_SearchDict) -> None:
        self._forward = forward
        self._reverse = reverse

    def _get_dict(self, reverse:bool) -> _SearchDict:
        return self._reverse if reverse else self._forward

    def search(self, pattern:str, count=None, *, reverse=False) -> MatchDict:
        """ Do a normal key string search for <pattern>.
            <count>   - Maximum number of matches returned. If None, there is no limit.
            <reverse> - If True, search for values instead of keys. """
        d = self._get_dict(reverse)
        keys = d.prefix_match_keys(pattern, count)
        return d.lookup(keys)

    def search_regex(self, pattern:str, count=None, *, reverse=False) -> MatchDict:
        """ Do a regular expression search for <pattern>. Return a special result if there's a regex syntax error.
            <count>   - Maximum number of matches returned. If None, there is no limit.
            <reverse> - If True, search for values instead of keys. """
        d = self._get_dict(reverse)
        try:
            keys = d.regex_match_keys(pattern, count)
        except RegexError:
            return {"INVALID REGEX": []}
        return d.lookup(keys)

    def search_nearby(self, pattern:str, count:int, *, reverse=False) -> MatchDict:
        """ Search for key strings close to <pattern>.
            <count>   - Maximum number of matches returned.
            <reverse> - If True, search for values instead of keys. """
        d = self._get_dict(reverse)
        keys = d.get_nearby_keys(pattern, count)
        return d.lookup(keys)


class StringSearchFactory:

    def __init__(self, strip_chars=" ") -> None:
        self._strip_chars = strip_chars

    def _simfn(self, s:str) -> str:
        """ Similarity function for search dicts that removes case and strips a user-defined set of symbols. """
        return s.strip(self._strip_chars).lower()

    def _simfn_mapped(self, s_iter:Iterable[str]) -> Iterable[str]:
        """ Mapping the built-in string methods separately provides a good speed boost for large dictionaries. """
        return map(str.lower, map(str.strip, s_iter, repeat(self._strip_chars)))

    def build(self, s_map:Mapping[str, str]) -> StringSearchEngine:
        """ Create new search dicts from a string mapping and the saved similarity functions. """
        kwargs = {"simfn": self._simfn,
                  "mapfn": self._simfn_mapped}
        forward = ForwardSearchDict(s_map, **kwargs)
        # This is the fastest way I could find to reverse a string dict
        # (even despite building and throwing away a giant list of None).
        rd = defaultdict(list)
        list(map(list.append, [rd[v] for v in s_map.values()], s_map))
        reverse = ReverseSearchDict(rd, **kwargs)
        return StringSearchEngine(forward, reverse)
