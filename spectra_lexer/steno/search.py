from typing import List

from .base import LX
from spectra_lexer.resource import StenoRule


class SearchEngine(LX):
    """ Master class for similar-key string lookups on one of many dictionaries grouped into resource types. """

    def LXSearchQuery(self, *args:str, index_key:str=None, **kwargs) -> List[str]:
        """ Choose an index to use based on keyword args and call a search on it. """
        if index_key is not None:
            return self.INDEX.search(index_key, *args, **kwargs)
        return self.TRANSLATIONS.search(*args, **kwargs)

    def LXSearchFindLink(self, rule:StenoRule) -> str:
        name = self.RULES.inverse.get(rule, "")
        if name not in self.INDEX:
            name = ""
        return name

    def LXSearchExamples(self, link_name:str, **kwargs) -> str:
        return self.INDEX.find_example(link_name, **kwargs)
