from typing import Dict, Tuple

from spectra_lexer.resource.keys import StenoKeyLayout
from spectra_lexer.resource.translations import ExamplesDict, RuleID, Translation, TranslationsDict
from spectra_lexer.search.index import RegexError, StripCaseIndex
from spectra_lexer.search.multidict import forward_multidict, reverse_multidict

MatchDict = Dict[str, Tuple[str, ...]]         # JSON-compatible dict of search results.
SearchData = Tuple[MatchDict, StripCaseIndex]  # Key search index paired with a standard dictionary for value lookup.

_EMPTY_DATA = ({}, StripCaseIndex())


class SearchEngine:
    """ A hybrid forward+reverse steno translation search engine.  """

    def __init__(self, strip_chars:str) -> None:
        self._strip_chars = strip_chars  # Characters to remove during search.
        self._tr_strokes = _EMPTY_DATA   # Forward translation search data (strokes -> text).
        self._tr_text = _EMPTY_DATA      # Reverse translation search data (text -> strokes).
        self._examples_raw = {}          # Contains steno rule IDs mapped to dicts of example translations.
        self._examples_cache = {}        # Cache of example search data for each rule ID and mode.

    def _build_index(self, d:MatchDict) -> StripCaseIndex:
        """ Build a new string search index that strips characters and removes case. """
        return StripCaseIndex(d, strip=self._strip_chars)

    def _compile_data(self, translations:TranslationsDict, mode_strokes:bool) -> SearchData:
        """ Compile string search data for <translations> in the correct direction for <mode_strokes>. """
        if mode_strokes:
            d = forward_multidict(translations)
        else:
            d = reverse_multidict(translations)
        return d, self._build_index(d)

    def set_translations(self, translations:TranslationsDict) -> None:
        """ Create new translation search data from the <translations> mapping. """
        self._tr_strokes = self._compile_data(translations, mode_strokes=True)
        self._tr_text = self._compile_data(translations, mode_strokes=False)

    def _get_translation_data(self, mode_strokes:bool) -> SearchData:
        """ Return the translation search data for <mode_strokes>. """
        return self._tr_strokes if mode_strokes else self._tr_text

    def search(self, pattern:str, count=None, *, mode_strokes=False, mode_regex=False) -> MatchDict:
        """ Do a normal translations search for <pattern>. Return a special result if there's a regex syntax error.
            <count>        - Maximum number of matches returned. If None, there is no limit.
            <mode_strokes> - If True, search for strokes instead of translations.
            <mode_regex>   - If True, do a regular expression search instead. """
        d, index = self._get_translation_data(mode_strokes)
        if mode_regex:
            try:
                keys = index.regex_match_keys(pattern, count)
            except RegexError:
                return {"INVALID REGEX": ()}
        else:
            keys = index.prefix_match_keys(pattern, count)
        return {k: d[k] for k in keys}

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

    def has_examples(self, rule_id:RuleID) -> bool:
        """ Return True if we have example translations under <rule_id>. """
        return rule_id in self._examples_raw

    def search_examples(self, rule_id:RuleID, pattern:str, count:int, *, mode_strokes=False) -> MatchDict:
        """ Search for translations close to <pattern> that contain examples of a particular steno rule.
            <rule_id>      - Identifier of the rule. Only exact matches will work.
            <count>        - Maximum number of matches returned.
            <mode_strokes> - If True, search for strokes instead of translations. """
        d, index = self._get_example_data(rule_id, mode_strokes)
        keys = index.get_nearby_keys(pattern, count)
        return {k: d[k] for k in keys}

    def random_examples(self, rule_id:RuleID, count:int, *, mode_strokes=False) -> MatchDict:
        """ Search for random translations using a particular steno rule.
            <rule_id>      - Identifier of the rule. Only exact matches will work.
            <count>        - Maximum number of matches returned.
            <mode_strokes> - If True, search for strokes instead of translations. """
        d, index = self._get_example_data(rule_id, mode_strokes)
        keys = index.get_random_keys(count)
        return {k: d[k] for k in keys}


def build_search_engine(keymap:StenoKeyLayout) -> SearchEngine:
    """ For translation-based searches, spaces and hyphens should be stripped off each end. """
    strip_chars = " " + keymap.divider_key()
    return SearchEngine(strip_chars)
