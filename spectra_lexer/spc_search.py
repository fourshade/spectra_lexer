import random

from spectra_lexer.resource.keys import StenoKeyLayout
from spectra_lexer.resource.translations import ExamplesDict, RuleID, Translation, TranslationsDict
from spectra_lexer.search.engine import MatchDict, StringSearchFactory


class SearchEngine:
    """ A hybrid forward+reverse steno translation search engine.  """

    def __init__(self, factory:StringSearchFactory) -> None:
        self._factory = factory
        self._main_engine = factory.build({})
        self._examples_raw = {}    # Contains steno rule IDs mapped to lists of example translations.
        self._examples_cache = {}  # Contains rule IDs mapped to subordinate search engines.

    def set_translations(self, translations:TranslationsDict) -> None:
        """ Create new translation search dicts from the <translations> mapping and saved similarity functions. """
        self._main_engine = self._factory.build(translations)

    def search(self, pattern:str, count=None, *, mode_strokes=False, mode_regex=False) -> MatchDict:
        """ Do a normal translations search for <pattern>.
            <count>        - Maximum number of matches returned. If None, there is no limit.
            <mode_strokes> - If True, search for strokes instead of translations.
            <mode_regex> - If True, do a regular expression search instead. """
        method = self._main_engine.search_regex if mode_regex else self._main_engine.search
        return method(pattern, count, reverse=not mode_strokes)

    def set_examples(self, examples:ExamplesDict) -> None:
        """ Set a new examples reference index and clear the cache of subengines built from the last one. """
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
            # Create and cache a new search dict to find examples for this rule id.
            translations = self._examples_raw.get(rule_id) or {}
            self._examples_cache[rule_id] = subengine = self._factory.build(translations)
        else:
            subengine = self._examples_cache[rule_id]
        return subengine.search_nearby(pattern, count, reverse=not mode_strokes)

    def random_example(self, rule_id:RuleID) -> Translation:
        """ Return a random translation using a particular steno rule by ID, or blank strings if none exist. """
        if not self.has_examples(rule_id):
            return "", ""
        translations = self._examples_raw[rule_id]
        samples = list(translations.items())
        return random.choice(samples)


def build_search_engine(keymap:StenoKeyLayout) -> SearchEngine:
    """ For translation-based searches, spaces and hyphens should be stripped off each end. """
    strip_chars = " " + keymap.divider_key()
    factory = StringSearchFactory(strip_chars)
    return SearchEngine(factory)
