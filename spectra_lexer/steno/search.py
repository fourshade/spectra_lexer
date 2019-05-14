from functools import partialmethod
from typing import List, Tuple

from .base import LX
from spectra_lexer.resource import StenoRule


class SearchEngine(LX):
    """ Master class for similar-key string lookups on one of many dictionaries grouped into resource types. """

    def _call_index(self, *args:str, index_key:str=None, meth_attr:str, **kwargs) -> List[str]:
        """ Choose an index to use based on keyword args and call a method on it. """
        if index_key is not None:
            index = self.INDEX
            args = (index_key, *args)
        else:
            index = self.TRANSLATIONS
        return getattr(index, meth_attr)(*args, **kwargs)

    LXSearchQuery = partialmethod(_call_index, meth_attr="search")
    LXSearchLookup = partialmethod(_call_index, meth_attr="lookup")

    def LXSearchFindLink(self, rule:StenoRule) -> str:
        name = self.RULES.inverse.get(rule, "")
        if name not in self.INDEX:
            name = ""
        return name

    def LXSearchExamples(self, link_name:str) -> Tuple[str, str]:
        """ Given a rule by name, return the search text, one translation using it at random, and its neighbors. """
        return self.INDEX.find_example(link_name)
