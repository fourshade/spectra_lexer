from collections import defaultdict
import random
from typing import Dict, List

from .dict import AbstractSearchIndex, ResourceSearchDict, INDEX_BY_PREFIX, INDEX_BY_RESOURCE
from ..index import LXIndex
from ..rules import StenoRule
from ..system import LXSystem
from ..translations import LXTranslations
from spectra_lexer.core import COREApp, Command, Component, Signal
from spectra_lexer.system import ConsoleCommand


class LXSearch:

    @ConsoleCommand("search_query")
    def search(self, pattern:str, **kwargs) -> List[str]:
        """ Determine the correct dict and perform a general search with the given mode. """
        raise NotImplementedError

    @ConsoleCommand("search_lookup")
    def lookup(self, pattern:str, match:str, **kwargs) -> list:
        """ Perform a normal dict lookup. We still require the original pattern to tell what dict it was. """
        raise NotImplementedError

    @Command
    def find_link(self, rule:StenoRule) -> str:
        """ Look for the given rule in the index. If there are examples, return the link reference. """
        raise NotImplementedError

    @Command
    def find_examples(self, **kwargs) -> tuple:
        """ If the link on the diagram is clicked, get a random translation using this rule and search near it. """
        raise NotImplementedError

    class FoundMatches:
        @Signal
        def on_search_found_matches(self, matches:List[str]) -> None:
            raise NotImplementedError

    class FoundMappings:
        @Signal
        def on_search_found_mappings(self, mappings:list) -> None:
            raise NotImplementedError

    class FoundExamples:
        @Signal
        def on_search_found_examples(self, search_text:str, matches:List[str], selected_match:str) -> None:
            raise NotImplementedError

    class FoundLink:
        @Signal
        def on_search_found_link(self, link_ref:str) -> None:
            raise NotImplementedError


class SearchEngine(Component, LXSearch,
                   LXSystem.Rules, LXTranslations.Dict, LXIndex.Dict):
    """ Master class for similar-key string lookups on one of many dictionaries grouped into resource types. """

    _collection: Dict[type, AbstractSearchIndex]  # Current collection of index objects, limited to one of each type.

    def __init__(self):
        self._collection = defaultdict(ResourceSearchDict)

    def __setattr__(self, attr, value):
        """ Make a new index, overwriting the previous one of the same type (if any). """
        super().__setattr__(attr, value)
        if attr in INDEX_BY_RESOURCE:
            cls = INDEX_BY_RESOURCE[attr]
            self._collection[cls] = cls(value)

    def search(self, *args, **kwargs) -> List[str]:
        return self._index_method("search", self.FoundMatches, *args, **kwargs)

    def lookup(self, *args, **kwargs) -> list:
        return self._index_method("lookup", self.FoundMappings, *args, **kwargs)

    def _index_method(self, attr:str, signal:type, pattern:str, *args, **kwargs) -> list:
        """ For any search, we must figure out which index to use and call it. """
        stripped, cls = INDEX_BY_PREFIX[pattern]
        index = self._collection[cls]
        items = getattr(index, attr)(stripped, *args, **kwargs)
        self.engine_call(signal, items)
        return items

    def find_link(self, rule:StenoRule) -> str:
        name = self.rules.inverted().get(rule)
        if name is not None and name in self.index:
            self.engine_call(self.FoundLink, name)
            return name
        return ""

    def find_examples(self, link_name:str, *, count:int=..., **kwargs) -> tuple:
        """ Given a rule by name, return the rule itself, one translation using it at random, and its neighbors. """
        search_text = f"//{link_name}"
        all_matches = self.search(search_text, prefix=True, **kwargs)
        item = random.choice(all_matches)
        search_text += f";{item}"
        nearby_matches = self.search(search_text, count=count, **kwargs)
        data = (search_text, nearby_matches, item)
        self.engine_call(self.FoundExamples, *data)
        return data
