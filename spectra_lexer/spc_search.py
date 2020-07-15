from typing import Dict, Tuple

from spectra_lexer.resource.translations import ExamplesDict, RuleID, TranslationsDict
from spectra_lexer.search.index import RegexError, StripCaseIndex
from spectra_lexer.search.multidict import forward_multidict, reverse_multidict

MatchDict = Dict[str, Tuple[str, ...]]         # JSON-compatible dict of search results.
SearchData = Tuple[MatchDict, StripCaseIndex]  # Key search index paired with a standard dictionary for value lookup.

INDEX_DELIM = ";;"                 # Delimiter between rule ID and query for example searches. Mostly arbitrary.
EXPAND_KEY = '[more...]'           # If present, repeating the search with a higher <count> will return more items.
BAD_REGEX_KEY = '[INVALID REGEX]'  # If present, the search input could not be compiled as a regular expression.

# Reserved string keys in every lookup dict. These (and only these) map to an empty tuple of values.
SENTINEL_KEYS = [EXPAND_KEY, BAD_REGEX_KEY]


def _to_search_data(d:MatchDict, strip_chars=" ") -> SearchData:
    """ Build a new string search index that strips characters and removes case. """
    index = StripCaseIndex(d, strip_chars)
    for k in SENTINEL_KEYS:
        d[k] = ()
    return d, index


_EMPTY_DATA = _to_search_data({})


class SearchEngine:
    """ A hybrid forward+reverse steno translation search engine with support for rule example lookup. """

    def __init__(self, strip_chars:str) -> None:
        self._strip_chars = strip_chars  # Characters to remove during search.
        self._tr_strokes = _EMPTY_DATA   # Forward translation search data (strokes -> text).
        self._tr_text = _EMPTY_DATA      # Reverse translation search data (text -> strokes).
        self._examples_raw = {}          # Contains steno rule IDs mapped to dicts of example translations.
        self._examples_cache = {}        # Cache of example search data for each rule ID and mode.

    def _compile_data(self, translations:TranslationsDict, mode_strokes:bool) -> SearchData:
        """ Compile string search data for <translations> in the correct direction for <mode_strokes>. """
        if mode_strokes:
            d = forward_multidict(translations)
        else:
            d = reverse_multidict(translations)
        return _to_search_data(d, self._strip_chars)

    def set_translations(self, translations:TranslationsDict) -> None:
        """ Create new translation search data from the <translations> mapping. """
        self._tr_strokes = self._compile_data(translations, mode_strokes=True)
        self._tr_text = self._compile_data(translations, mode_strokes=False)

    def _get_translation_data(self, mode_strokes:bool) -> SearchData:
        """ Return the translation search data for <mode_strokes>. """
        return self._tr_strokes if mode_strokes else self._tr_text

    def set_examples(self, examples:ExamplesDict) -> None:
        """ Set a new examples reference dict and clear any cached data from the last one. """
        self._examples_raw = examples
        self._examples_cache.clear()

    def _get_example_data(self, rule_id:RuleID, mode_strokes:bool) -> SearchData:
        """ Return the example search data for <rule_id> in <mode_strokes>.
            Create and cache a new data set if it doesn't exist yet. """
        key = (rule_id, mode_strokes)
        if key not in self._examples_cache:
            translations = self._examples_raw.get(rule_id) or {}
            self._examples_cache[key] = self._compile_data(translations, mode_strokes)
        return self._examples_cache[key]

    def search(self, pattern:str, count=None, *, mode_strokes=False, mode_regex=False) -> MatchDict:
        """ Perform a translations search for <pattern>. Return a special result if there's a regex syntax error.
            If there is an index delimiter, search for rule examples instead. Only exact matches will work there.
            <count>        - Maximum number of matches returned. If None, there is no limit.
            <mode_strokes> - If True, search for strokes instead of translations.
            <mode_regex>   - If True, do a regular expression search instead. """
        if not pattern.strip():
            return {}
        if INDEX_DELIM in pattern:
            rule_id, tr_pattern = pattern.split(INDEX_DELIM, 1)
            d, index = self._get_example_data(rule_id, mode_strokes)
            keys = index.get_nearby_keys(tr_pattern, count or len(index))
        else:
            d, index = self._get_translation_data(mode_strokes)
            method = index.regex_match_keys if mode_regex else index.prefix_match_keys
            if count is None:
                count = len(index)
            try:
                # Search for one more item than requested so we can tell if adding a page will add results.
                keys = method(pattern, count + 1)
                if len(keys) > count:
                    keys[-1] = EXPAND_KEY
            except RegexError:
                keys = [BAD_REGEX_KEY]
        return {k: d[k] for k in keys}

    def has_examples(self, rule_id:RuleID) -> bool:
        """ Return True if we have example translations under <rule_id>. """
        return rule_id in self._examples_raw

    def random_pattern(self, rule_id:RuleID, *, mode_strokes=False) -> str:
        """ Return a valid example search pattern for <rule_id> centered on a random translation if one exists.
            <rule_id>      - Identifier of the rule. Only exact matches will work.
            <mode_strokes> - If True, search for strokes instead of translations. """
        _, index = self._get_example_data(rule_id, mode_strokes)
        keys = index.get_random_keys(1)
        if not keys:
            return ""
        return rule_id + INDEX_DELIM + keys[0]
