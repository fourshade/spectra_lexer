import random
import re
from itertools import repeat
from typing import Dict, Iterable, List

from .dict import ReverseDict, StringSearchDict


class SearchResults:

    def __init__(self, matches:List[str], mappings:List[List[str]], is_complete=True) -> None:
        self.matches = matches          # List of matched strings.
        self.mappings = mappings        # List of mappings for each match in order.
        self.is_complete = is_complete  # If True, this includes all available results.


class StenoSearchDict(StringSearchDict):
    """ Abstract class for a string search dict with methods specifically for steno translations. """

    def search(self, pattern:str, *, count:int=None) -> SearchResults:
        """ Perform a prefix search for <pattern> limited to <count> matches, or no limit if <count> is None. """
        matches = self.prefix_match_keys(pattern, count)
        return self._compile_results(matches, count)

    def search_regex(self, pattern:str, *, count:int=None) -> SearchResults:
        """ Perform a regex search for <pattern> limited to <count> matches, or no limit if <count> is None.
            Return a warning match with no mappings if there's a regex syntax error. """
        try:
            matches = self.regex_match_keys(pattern, count)
            return self._compile_results(matches, count)
        except re.error:
            return SearchResults(["REGEX ERROR"], [])

    def search_nearby(self, pattern:str, *, count:int) -> SearchResults:
        matches = self.get_nearby_keys(pattern, count=count)
        return self._compile_results(matches, count)

    def _compile_results(self, matches:List[str], count:int=None) -> SearchResults:
        """ Populate a results structure with matches and mappings. """
        mappings = [self._lookup(m) for m in matches]
        is_complete = count is None or len(matches) < count
        return SearchResults(matches, mappings, is_complete)

    def _lookup(self, match:str) -> List[str]:
        """ Look up a match key and return its value in a list. The key must exist. """
        raise NotImplementedError


class ForwardStenoSearchDict(StenoSearchDict):
    """ Forward translations dict (strokes -> English words). """

    def _lookup(self, match:str) -> List[str]:
        """ Forward dict values are strings; wrap each one in a list. """
        return [self[match]]


class ReverseStenoSearchDict(StenoSearchDict):
    """ Reverse translations dict (English words -> strokes). """

    def _lookup(self, match:str) -> List[str]:
        """ Reverse dict values are already lists. """
        return self[match]


class StripCaseFunctions:
    """ Contains similarity functions for search dicts that remove case and strip a user-defined set of symbols. """

    def __init__(self, strip_chars=" ") -> None:
        self._strip_chars = strip_chars  # Characters to strip off each end.

    def simfn(self, s:str) -> str:
        return s.strip(self._strip_chars).lower()

    def mapfn(self, s_iter:Iterable[str]) -> map:
        """ Mapping the built-in string methods separately provides a good speed boost for large dictionaries. """
        return map(str.lower, map(str.strip, s_iter, repeat(self._strip_chars)))


class TranslationSearchEngine:
    """ A hybrid forward+reverse steno translation search engine. """

    def __init__(self, translations:Dict[str, str]=None, strip_chars=" -") -> None:
        """ For translation-based searches, spaces and hyphens should be stripped off each end by default. """
        fd = translations or {}
        rd = ReverseDict.from_forward(fd)
        fns = StripCaseFunctions(strip_chars)
        kwargs = dict(simfn=fns.simfn, mapfn=fns.mapfn)
        self._forward = ForwardStenoSearchDict(fd, **kwargs)  # Forward translations dict (strokes -> English words).
        self._reverse = ReverseStenoSearchDict(rd, **kwargs)  # Reverse dict (English words -> strokes).

    def search(self, pattern:str, *, count=100, strokes=False, regex=False) -> SearchResults:
        """ Delegate searches to one of the translations dicts depending on <strokes>.
            Search for matches in that dict. Use regular expression matching if <regex> is True. """
        d = self._forward if strokes else self._reverse
        if regex:
            return d.search_regex(pattern, count=count)
        else:
            return d.search(pattern, count=count)

    def search_nearby(self, pattern:str, *, count=100, strokes=False) -> SearchResults:
        d = self._forward if strokes else self._reverse
        return d.search_nearby(pattern, count=count)

    def to_dict(self) -> Dict[str, str]:
        """ Return all of the original translations in a normal dict. """
        return dict(self._forward)


class ExampleSearchEngine:

    def __init__(self, examples:Dict[str, dict]=None) -> None:
        """ Load a new example search index. Make sure the index is a dict of dicts and not arbitrary JSON. """
        if examples is None:
            examples = {}
        elif not isinstance(examples, dict) or not all([isinstance(v, dict) for v in examples.values()]):
            raise TypeError("An example index must be a dict of dicts.")
        self._examples = examples

    def search(self, rule_name:str, pattern="", *, count=None, strokes=False) -> SearchResults:
        """ Search for translations that contain examples of a particular steno rule. Only exact matches will work.
            If there's no pattern, return results starting at a random location.
            <strokes> - if True, the pattern will be interpreted as a steno key string. """
        d = self._examples.get(rule_name)
        if d is None:
            return SearchResults([], [])
        if pattern and count is not None:
            e = TranslationSearchEngine(d)
            return e.search_nearby(pattern, count=count, strokes=strokes)
        keys = list(d)
        values = list(d.values())
        matches, mappings = (keys, values) if strokes else (values, keys)
        if count is not None:
            free_space = len(d) - count
            if free_space > 0:
                start = random.randint(0, free_space)
                end = start + count
                matches = matches[start:end]
                mappings = mappings[start:end]
        mappings = [[m] for m in mappings]
        return SearchResults(matches, mappings)

    def __contains__(self, rule_name:str) -> bool:
        """ Return True if we have examples of <rule_name>. """
        return rule_name in self._examples
