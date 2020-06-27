from collections import defaultdict
from itertools import repeat
from typing import Dict, Iterable, List, Mapping

from .dict import RegexError, StringSearchDict

StringIter = Iterable[str]
StringList = List[str]
StringMap = Mapping[str, str]
MatchDict = Dict[str, StringList]
ForwardSearchDict = StringSearchDict[str]
ReverseSearchDict = StringSearchDict[StringList]


class StringSearchEngine:
    """ A hybrid forward+reverse string search engine.  """

    def __init__(self, forward:ForwardSearchDict, reverse:ReverseSearchDict) -> None:
        self._forward = forward
        self._reverse = reverse

    def _get_dict(self, reverse:bool) -> StringSearchDict:
        return self._reverse if reverse else self._forward

    def _compile_matches(self, keys:StringIter, reverse:bool) -> MatchDict:
        """ Return a dictionary with each key mapped to a list of matching values. All keys must exist. """
        d = self._get_dict(reverse)
        if reverse:
            # Reverse dict values are already lists; copy each one.
            matches = {k: [*d[k]] for k in keys}
        else:
            # Forward dict values are strings; wrap each one in a list.
            matches = {k: [d[k]] for k in keys}
        return matches

    def search(self, pattern:str, count=None, *, reverse=False) -> MatchDict:
        """ Do a normal key string search for <pattern>.
            <count>   - Maximum number of matches returned. If None, there is no limit.
            <reverse> - If True, search for values instead of keys. """
        d = self._get_dict(reverse)
        keys = d.prefix_match_keys(pattern, count)
        return self._compile_matches(keys, reverse)

    def search_regex(self, pattern:str, count=None, *, reverse=False) -> MatchDict:
        """ Do a regular expression search for <pattern>. Return a special result if there's a regex syntax error.
            <count>   - Maximum number of matches returned. If None, there is no limit.
            <reverse> - If True, search for values instead of keys. """
        d = self._get_dict(reverse)
        try:
            keys = d.regex_match_keys(pattern, count)
        except RegexError:
            return {"INVALID REGEX": []}
        return self._compile_matches(keys, reverse)

    def search_nearby(self, pattern:str, count:int, *, reverse=False) -> MatchDict:
        """ Search for key strings close to <pattern>.
            <count>   - Maximum number of matches returned.
            <reverse> - If True, search for values instead of keys. """
        d = self._get_dict(reverse)
        keys = d.get_nearby_keys(pattern, count)
        return self._compile_matches(keys, reverse)


class StringSearchFactory:

    def __init__(self, strip_chars=" ") -> None:
        self._strip_chars = strip_chars  # Characters to ignore at the ends of strings during search.

    def _simfn(self, s:str) -> str:
        """ Similarity function for search dicts that removes case and strips a user-defined set of symbols. """
        return s.strip(self._strip_chars).lower()

    def _simfn_mapped(self, s_iter:StringIter) -> StringIter:
        """ Mapping the built-in string methods separately provides a good speed boost for large dictionaries. """
        return map(str.lower, map(str.strip, s_iter, repeat(self._strip_chars)))

    def _new_dict(self, *args) -> StringSearchDict:
        """ Create a new search dict using the saved similarity functions. """
        return StringSearchDict(*args, simfn=self._simfn, mapfn=self._simfn_mapped)

    def _build_forward(self, s_map:StringMap) -> ForwardSearchDict:
        """ Create a normal search dict from a string mapping. """
        return self._new_dict(s_map)

    def _build_reverse(self, s_map:StringMap) -> ReverseSearchDict:
        """ This is the fastest way I could find to reverse a string dict
            (even despite building and throwing away a giant list of None). """
        rd = defaultdict(list)
        list(map(list.append, [rd[v] for v in s_map.values()], s_map))
        return self._new_dict(rd)

    def build(self, s_map:StringMap) -> StringSearchEngine:
        """ Build a bidirectional string search engine. """
        forward = self._build_forward(s_map)
        reverse = self._build_reverse(s_map)
        return StringSearchEngine(forward, reverse)
