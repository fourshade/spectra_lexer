from collections import defaultdict
from itertools import repeat
import random
import re
from typing import Dict, Hashable, Iterable, Mapping, List, Tuple

from .dict import StringSearchDict

MatchDict = Dict[str, List[str]]                  # Dict matching search strings to lists of possible values.
Translation = Tuple[str, str]                     # A steno key string paired with its translation string.
TranslationsMap = Mapping[str, str]               # Mapping of steno key strings to translation strings.
RuleID = Hashable                                 # Rule ID data type. Can be anything hashable.
ExamplesMap = Mapping[RuleID, List[Translation]]  # Mapping of rule identifiers to lists of example translations.


class SearchRegexError(Exception):
    """ Raised if there's a syntax error in a regex search. """


class SearchEngine:
    """ A hybrid forward+reverse steno translation search engine.  """

    def __init__(self, strip_chars=" -") -> None:
        """ For translation-based searches, spaces and hyphens should be stripped off each end by default. """
        self._strip_chars = strip_chars
        self._forward = StringSearchDict()  # Forward translations dict (strokes -> English words).
        self._reverse = StringSearchDict()  # Reverse translations dict (English words -> strokes).
        self._examples_raw = {}             # Contains steno rule IDs mapped to lists of example translations.
        self._examples_cache = {}           # Contains (rule ID, mode) pairs mapped to search dicts.

    def _simfn(self, s:str) -> str:
        """ Similarity function for search dicts that removes case and strips a user-defined set of symbols. """
        return s.strip(self._strip_chars).lower()

    def _simfn_mapped(self, s_iter:Iterable[str]) -> Iterable[str]:
        """ Mapping the built-in string methods separately provides a good speed boost for large dictionaries. """
        return map(str.lower, map(str.strip, s_iter, repeat(self._strip_chars)))

    def _new_search_dict(self, translations:TranslationsMap, *, reverse=False) -> StringSearchDict:
        """ Return a StringSearchDict that uses our strip functions. """
        if reverse:
            # This is the fastest way I could find to reverse a string dict
            # (even despite building and throwing away a giant list of None).
            d = defaultdict(list)
            list(map(list.append, [d[v] for v in translations.values()], translations))
        else:
            d = translations
        return StringSearchDict(d, simfn=self._simfn, mapfn=self._simfn_mapped)

    def set_translations(self, translations:TranslationsMap) -> None:
        """ Create new translation search dicts from the <translations> mapping and saved similarity functions. """
        self._forward = self._new_search_dict(translations)
        self._reverse = self._new_search_dict(translations, reverse=True)

    def _get_dict(self, mode_strokes:bool) -> StringSearchDict:
        return self._forward if mode_strokes else self._reverse

    @staticmethod
    def _lookup_keys(d:StringSearchDict, keys:Iterable[str], wrap=False) -> MatchDict:
        """ Forward dict values are strings; wrap each one in a list.
            Reverse dict values are already lists; copy each one. """
        if wrap:
            return {k: [d[k]] for k in keys}
        else:
            return {k: [*d[k]] for k in keys}

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
        key = (rule_id, mode_strokes)
        if key not in self._examples_cache:
            # Create and cache a new search dict to find examples for this rule id and mode.
            translations = dict(self._examples_raw.get(rule_id, ()))
            self._examples_cache[key] = self._new_search_dict(translations, reverse=not mode_strokes)
        d = self._examples_cache[key]
        keys = d.get_nearby_keys(pattern, count)
        return self._lookup_keys(d, keys, mode_strokes)

    def random_example(self, rule_id:RuleID) -> Translation:
        """ Return a random translation using a particular steno rule by ID, or blank strings if none exist. """
        examples_list = self._examples_raw.get(rule_id) or [("", "")]
        return random.choice(examples_list)
