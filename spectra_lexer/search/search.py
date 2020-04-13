""" Module for specific steno translation search dictionaries and managers. """

from functools import lru_cache
from itertools import repeat
import random
import re
from typing import Dict, Hashable, Iterable, Mapping, List, Tuple

from .dict import ReverseDict, StringSearchDict

MatchDict = Dict[str, List[str]]                # Dict matching search strings to lists of possible values.
TranslationsMap = Mapping[str, str]             # Mapping of steno key strings to translation strings.
RuleID = Hashable                               # Rule ID data type. Can be anything hashable.
ExamplesMap = Mapping[RuleID, TranslationsMap]  # Mapping of rule identifiers to collections of example translations.


class BaseStenoDict(StringSearchDict):
    """ Abstract class for a string search dict with methods specifically for steno translations. """

    def lookup(self, keys:List[str]) -> MatchDict:
        """ Look up match keys and return each value in a list. Every key must exist. """
        raise NotImplementedError


class ForwardStenoDict(BaseStenoDict):
    """ Forward translations dict (strokes -> English words). """

    def lookup(self, keys:List[str]) -> MatchDict:
        """ Forward dict values are strings; wrap each one in a list. """
        return {k: [self[k]] for k in keys}


class ReverseStenoDict(ReverseDict, BaseStenoDict):
    """ Reverse translations dict (English words -> strokes). """

    def lookup(self, keys:List[str]) -> MatchDict:
        """ Reverse dict values are already lists. """
        return {k: self[k] for k in keys}


class StripCaseFunctions:
    """ Contains similarity functions for search dicts that remove case and strip a user-defined set of symbols. """

    def __init__(self, strip_chars=" ") -> None:
        self._strip_chars = strip_chars  # Characters to strip off each end.

    def simfn(self, s:str) -> str:
        return s.strip(self._strip_chars).lower()

    def mapfn(self, s_iter:Iterable[str]) -> map:
        """ Mapping the built-in string methods separately provides a good speed boost for large dictionaries. """
        return map(str.lower, map(str.strip, s_iter, repeat(self._strip_chars)))


class SearchResults:
    """ Data class for all results of a search. """

    def __init__(self, matches:MatchDict=None, is_complete=True) -> None:
        self.matches = matches or {}    # Dict of matched strings with a list of mappings for each.
        self.is_complete = is_complete  # If True, this includes all available results.


class SearchEngine:
    """ A hybrid forward+reverse steno translation search engine.  """

    _forward = ForwardStenoDict()  # Forward translations dict (strokes -> English words).
    _reverse = ReverseStenoDict()  # Reverse dict (English words -> strokes).
    _examples = {}                 # Contains steno rule IDs mapped to dicts of example translations.

    def __init__(self, strip_chars=" -") -> None:
        """ For translation-based searches, spaces and hyphens should be stripped off each end by default. """
        self._strip_chars = strip_chars

    def set_translations(self, translations:TranslationsMap) -> None:
        """ Create new translation search dicts from the <translations> mapping and saved similarity functions. """
        self._forward = self._new_forward_dict(translations)
        self._reverse = self._new_reverse_dict(translations)

    def _new_forward_dict(self, translations:TranslationsMap) -> BaseStenoDict:
        return ForwardStenoDict(translations, **self._strip_kwargs())

    def _new_reverse_dict(self, translations:TranslationsMap) -> BaseStenoDict:
        return ReverseStenoDict.from_forward(translations, **self._strip_kwargs())

    def _strip_kwargs(self) -> dict:
        """ Return a dict of kwargs with strip functions for the SimilarKeyDict constructor. """
        fns = StripCaseFunctions(self._strip_chars)
        return {"simfn": fns.simfn, "mapfn": fns.mapfn}

    def set_examples(self, examples:Mapping[RuleID, TranslationsMap]) -> None:
        """ Set a new examples reference index and clear the cache of any search dicts built from the last one. """
        self._examples = examples
        self._example_search_dict.cache_clear()

    @lru_cache(maxsize=None)
    def _example_search_dict(self, rule_id:RuleID, is_forward:bool) -> BaseStenoDict:
        """ Make a new search dict to find rule examples from a normal dict under <rule_id> and cache it. """
        d = self._examples[rule_id]
        return self._new_forward_dict(d) if is_forward else self._new_reverse_dict(d)

    def search_translations(self, pattern:str, count=None, *, mode_strokes=False, mode_regex=False) -> SearchResults:
        """ Do a new translations search. Return a warning match with no mappings if there's a regex syntax error.
            <count>        - Maximum number of matches returned. If None, there is no limit.
            <mode_strokes> - If True, search for strokes instead of translations.
            <mode_regex>   - If True, treat the search pattern as a regular expression. """
        d = self._forward if mode_strokes else self._reverse
        method = d.regex_match_keys if mode_regex else d.prefix_match_keys
        try:
            keys = method(pattern, count)
            matches = d.lookup(keys)
            is_complete = count is None or len(matches) < count
        except re.error:
            matches = {"REGEX ERROR": []}
            is_complete = True
        return SearchResults(matches, is_complete)

    def search_examples(self, rule_id:RuleID, pattern:str, count:int, *, mode_strokes=False) -> SearchResults:
        """ Search for translations that contain examples of a particular steno rule. Only exact matches will work.
            Since this can return results until exhaustion, these searches are always marked "complete". """
        if rule_id not in self._examples:
            matches = {}
        else:
            search_dict = self._example_search_dict(rule_id, mode_strokes)
            keys = search_dict.get_nearby_keys(pattern, count)
            matches = search_dict.lookup(keys)
        return SearchResults(matches, True)

    def random_example(self, rule_id:RuleID) -> Tuple[str, str]:
        """ Return a random valid translation using a steno rule. """
        d = self._examples.get(rule_id)
        if not d:
            return "", ""
        items = list(d.items())
        return random.choice(items)

    def has_examples(self, rule_id:RuleID) -> bool:
        """ Return True if we have example translations under <rule_id>. """
        return rule_id in self._examples
