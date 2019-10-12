import random
import re
from typing import Dict, List, Tuple

from .dict import ReverseDict, StringSearchDict


class TranslationsSearchEngine:
    """ A hybrid forward+reverse steno translation search engine. """

    def __init__(self, d:Dict[str, str]=None, strip_chars=" -") -> None:
        """ For translation-based searches, spaces and hyphens should be stripped off each end by default. """
        forward = StringSearchDict.strip_case(d or {}, _strip=strip_chars)
        rev_dict = ReverseDict.from_forward(forward)
        reverse = StringSearchDict.strip_case(rev_dict, _strip=strip_chars)
        self._forward = forward  # Forward translations dict (strokes -> English words).
        self._reverse = reverse  # Reverse dict (English words -> strokes).

    def search(self, pattern:str, count:int=None, strokes=False, prefix=True, regex=False) -> List[str]:
        """ Perform a special search for <pattern> with the given flags. Return up to <count> matches.
            If <count> is None, perform a normal lookup instead. The dict only depends on the strokes mode. """
        d = self._forward if strokes else self._reverse
        if count is None:
            # Make sure to wrap the result in a list. Reverse dict values are always lists.
            v = d.get(pattern)
            if v:
                return [v] if strokes else v
            return []
        if regex:
            try:
                return d.regex_match_keys(pattern, count)
            except re.error:
                return ["REGEX ERROR"]
        if prefix:
            return d.prefix_match_keys(pattern, count)
        return d.get_nearby_keys(pattern, count)


class ExampleSearchEngine:
    """ A resource-heavy search engine for finding translations that contain examples of a particular steno rule.
        Example search is a two-part search. The first part goes by rule name; only exact matches will work. """

    def __init__(self, index:Dict[str, dict]=None) -> None:
        """ Make sure the index is a dict of dicts and not arbitrary JSON. """
        if index is None:
            index = {}
        elif not isinstance(index, dict) or not all([isinstance(v, dict) for v in index.values()]):
            raise TypeError("An example index must be a dict of dicts.")
        self._index = index         # Contains a raw dict of example translations for each rule.
        self._search_engines = {}   # Holds all indices converted to search engines.

    def search(self, rule_name:str, pattern:str, **kwargs) -> List[str]:
        """ Translation search dicts are memory hogs, and users tend to look at many results under the same rule.
            Convert native dicts (from JSON) to full-featured search engines only on demand. """
        search_engine = self._search_engines.get(rule_name)
        if not search_engine:
            d = self._index.get(rule_name)
            if not d:
                return []
            search_engine = self._search_engines[rule_name] = TranslationsSearchEngine(d)
        # Manually set the search flags.
        kwargs.update(prefix=False, regex=False)
        return search_engine.search(pattern, **kwargs)

    def has_examples(self, rule_name:str) -> bool:
        """ Return True if we have examples of <rule_name>. """
        return rule_name in self._index

    def random_example(self, rule_name:str) -> Tuple[str, str]:
        """ Find one translation (if any) using <rule_name> at random. """
        d = self._index.get(rule_name)
        if not d:
            return "", ""
        k = random.choice(list(d))
        return k, d[k]

    def __repr__(self) -> str:
        """ Recursive reprs on index objects are deadly. Only show the first level with item counts. """
        item_counts = {k: f"{len(v)} items" for k, v in self._index.items()}
        return f"<{type(self).__name__}: {item_counts!r}>"


class SearchEngine:
    """ Uses specially created search dictionaries to find translations using a variety of methods. """

    def __init__(self) -> None:
        self._translations = TranslationsSearchEngine()
        self._index = ExampleSearchEngine()

    def set_translations(self, translations:Dict[str, str]) -> None:
        """ Load a new translations search dict. """
        self._translations = TranslationsSearchEngine(translations)

    def set_index(self, index:Dict[str, dict]) -> None:
        """ Load a new example search index. """
        self._index = ExampleSearchEngine(index)

    def search_translations(self, pattern:str, **kwargs) -> List[str]:
        """ Search for matches in the translations index. """
        return self._translations.search(pattern, **kwargs)

    def search_examples(self, rule_name:str, pattern:str, **kwargs) -> List[str]:
        """" Search for matches in the examples index. """
        return self._index.search(rule_name, pattern, **kwargs)

    def has_examples(self, rule_name:str) -> bool:
        """ Return True if we have examples of <rule_name>. """
        return self._index.has_examples(rule_name)

    def find_example(self, rule_name:str) -> Tuple[str, str]:
        """ Given a rule by name, return one translation using it at random. """
        return self._index.random_example(rule_name)
