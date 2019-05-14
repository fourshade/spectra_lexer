from typing import List, Tuple

from .base import LX
from spectra_lexer.resource import StenoRule

_INDEX_PREFIX: str = "//"  # Prefix in search input to indicate an index search.
_INDEX_DELIM: str = ";"    # Delimiter between rule name and translation.


class SearchEngine(LX):
    """ Master class for similar-key string lookups on one of many dictionaries grouped into resource types. """

    def LXSearchQuery(self, pattern:str, **kwargs) -> List[str]:
        pattern, index = self._get_index(pattern, kwargs)
        return index.search(pattern, **kwargs)

    def LXSearchLookup(self, pattern:str, match:str, **kwargs) -> List[str]:
        _, index = self._get_index(pattern, kwargs)
        return index.lookup(match, **kwargs)

    def _get_index(self, pattern:str, kwargs:dict) -> tuple:
        """ For any search, we must figure out which index to use. """
        if pattern.startswith(_INDEX_PREFIX):
            kwargs["index_key"], pattern = (pattern[len(_INDEX_PREFIX):].split(_INDEX_DELIM, 1) + [""])[:2]
            return pattern, self.INDEX
        else:
            return pattern, self.TRANSLATIONS

    def LXSearchFindLink(self, rule:StenoRule) -> str:
        name = self.RULES.inverse.get(rule)
        if name is not None and name in self.INDEX:
            return name
        return ""

    def LXSearchExamples(self, link_name:str, strokes:bool=False, **kwargs) -> Tuple[str, str]:
        """ Given a rule by name, return the search text, one translation using it at random, and its neighbors. """
        item = self.INDEX.find_example(link_name)[not strokes]
        search_text = _INDEX_PREFIX + link_name + _INDEX_DELIM + item
        return search_text, item
