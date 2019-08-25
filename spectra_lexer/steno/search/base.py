from typing import Dict, List, Tuple

from .index import StenoIndex
from .translations import TranslationsDictionary
from ..rules import StenoRule


class SearchEngine:
    """ Uses specially created search dictionaries to find entries using a variety of methods. """

    INDEX_DELIM: str = ";"  # Delimiter between rule name and query for index searches.

    _rules: Dict[str, StenoRule]
    _translations: TranslationsDictionary
    _index: StenoIndex
    _indexed_rule_names: Dict[StenoRule, str]

    def __init__(self, rules:Dict[str, StenoRule]) -> None:
        self._rules = rules
        self.load_translations({})
        self.load_index({})

    def load_translations(self, translations:Dict[str, str]) -> None:
        """ Load a new translations search dict. """
        self._translations = TranslationsDictionary(translations)

    def load_index(self, index:Dict[str, dict]) -> None:
        """ Load a new search index and populate a dict with names that are found both there and in the rules dict. """
        rules = self._rules
        self._index = StenoIndex(index)
        self._indexed_rule_names = {rules[name]: name for name in index if name in rules}

    def search(self, pattern:str, match:str=None, **kwargs) -> List[str]:
        """ Choose an index to use based on delimiters in the input pattern.
            Search for matches in that index. If <match> is given, the search will find mappings instead. """
        *keys, pattern = pattern.split(self.INDEX_DELIM, 1)
        index = self._index if keys else self._translations
        return index.search(*keys, match or pattern, **kwargs)

    def find_example(self, link:str, **kwargs) -> Tuple[str, str]:
        """ Find an example translation in the index for the given link and return it with the required input text. """
        selection = self._index.find_example(link, **kwargs)
        text = self.INDEX_DELIM.join([link, selection])
        return selection, text

    def rule_to_link(self, rule:StenoRule) -> str:
        """ Return the name of the given rule to use in a link, but only if it has examples in the index. """
        return self._indexed_rule_names.get(rule) or ""

    def link_to_rule(self, link:str) -> StenoRule:
        """ Return the rule under the given link name, or None if there is no rule by that name. """
        return self._rules.get(link)
