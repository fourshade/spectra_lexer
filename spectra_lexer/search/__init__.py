""" Package for the steno translation search engine.
    Includes specific steno translation search dictionaries and managers. """

from collections import defaultdict
from itertools import repeat
import random
import re
from typing import Dict, Hashable, Iterable, Mapping, List, Tuple

from .dict import StringSearchDict

MatchDict = Dict[str, List[str]]                # Dict matching search strings to lists of possible values.
TranslationsMap = Mapping[str, str]             # Mapping of steno key strings to translation strings.
RuleID = Hashable                               # Rule ID data type. Can be anything hashable.
ExamplesMap = Mapping[RuleID, TranslationsMap]  # Mapping of rule identifiers to collections of example translations.


class SearchRegexError(Exception):
    """ Raised if there's a syntax error in a regex search. """


class SearchEngine:
    """ A hybrid forward+reverse steno translation search engine.  """

    def __init__(self, strip_chars=" -") -> None:
        """ For translation-based searches, spaces and hyphens should be stripped off each end by default. """
        self._strip_chars = strip_chars
        self._forward = StringSearchDict()  # Forward translations dict (strokes -> English words).
        self._reverse = StringSearchDict()  # Reverse translations dict (English words -> strokes).
        self._examples_raw = {}             # Contains steno rule IDs mapped to dicts of example translations.
        self._examples_cache = {}           # Contains steno rule IDs mapped to pairs of search dicts.

    def _simfn(self, s:str) -> str:
        """ Similarity function for search dicts that removes case and strips a user-defined set of symbols. """
        return s.strip(self._strip_chars).lower()

    def _simfn_mapped(self, s_iter:Iterable[str]) -> Iterable[str]:
        """ Mapping the built-in string methods separately provides a good speed boost for large dictionaries. """
        return map(str.lower, map(str.strip, s_iter, repeat(self._strip_chars)))

    def _new_search_dict(self, *args) -> StringSearchDict:
        """ Return a StringSearchDict that uses our strip functions. """
        return StringSearchDict(*args, simfn=self._simfn, mapfn=self._simfn_mapped)

    def _new_dict_pair(self, translations:TranslationsMap) -> List[StringSearchDict]:
        """ Create new translation search dicts from the <translations> mapping and saved similarity functions. """
        rdict = defaultdict(list)
        list(map(list.append, [rdict[v] for v in translations.values()], translations))
        return [*map(self._new_search_dict, [translations, rdict])]

    def set_translations(self, translations:TranslationsMap) -> None:
        self._forward, self._reverse = self._new_dict_pair(translations)

    def _get_dict(self, mode_strokes:bool) -> StringSearchDict:
        return self._forward if mode_strokes else self._reverse

    @staticmethod
    def _lookup_keys(d:StringSearchDict, keys:Iterable[str], wrap=False) -> MatchDict:
        """ Forward dict values are strings; wrap each one in a list.
            Reverse dict values are already lists; copy each one. """
        if wrap:
            return {k: [d[k]] for k in keys}
        else:
            return {k: d[k][:] for k in keys}

    def search(self, pattern:str, count=None, *, mode_strokes=False) -> MatchDict:
        """ Do a normal translations search for <pattern>.
            <count>        - Maximum number of matches returned. If None, there is no limit.
            <mode_strokes> - If True, search for strokes instead of translations. """
        d = self._get_dict(mode_strokes)
        keys = d.prefix_match_keys(pattern, count)
        return self._lookup_keys(d, keys, mode_strokes)

    def search_regex(self, pattern:str, count=None, *, mode_strokes=False) -> MatchDict:
        """ Do a regular expression search for <pattern>. Raise a special exception if there's a regex syntax error.
            <count>        - Maximum number of matches returned. If None, there is no limit.
            <mode_strokes> - If True, search for strokes instead of translations. """
        d = self._get_dict(mode_strokes)
        try:
            keys = d.regex_match_keys(pattern, count)
        except re.error as e:
            raise SearchRegexError(pattern) from e
        return self._lookup_keys(d, keys, mode_strokes)

    def set_examples(self, examples:ExamplesMap) -> None:
        """ Set a new examples reference index and clear the cache of any search dicts built from the last one. """
        self._examples_raw = examples
        self._examples_cache.clear()

    def has_examples(self, rule_id:RuleID) -> bool:
        """ Return True if we have example translations under <rule_id>. """
        return rule_id in self._examples_raw

    def search_examples(self, rule_id:RuleID, pattern:str, count:int, *, mode_strokes=False) -> MatchDict:
        """ Search for translations close to <pattern> that contain examples of a particular steno rule.
            <rule_id>      - Identifier of the rule. Only exact matches will work.
            <count>        - Maximum number of matches returned.
            <mode_strokes> - If True, search for strokes instead of translations. """
        if rule_id not in self._examples_cache:
            # Make a new search dict to find rule examples from a normal dict under <rule_id> and cache it.
            translations = self._examples_raw.get(rule_id) or {}
            self._examples_cache[rule_id] = self._new_dict_pair(translations)
        d = self._examples_cache[rule_id][not mode_strokes]
        keys = d.get_nearby_keys(pattern, count)
        return self._lookup_keys(d, keys, mode_strokes)

    def random_example(self, rule_id:RuleID) -> Tuple[str, str]:
        """ Return a random translation using a particular steno rule by ID, or blank strings if none exist. """
        translations = self._examples_raw.get(rule_id)
        if not translations:
            return "", ""
        keys = list(translations)
        k = random.choice(keys)
        return k, translations[k]
