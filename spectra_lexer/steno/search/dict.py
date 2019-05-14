""" Module with instances and groupings of specialized string search dictionaries by the resource they represent. """

from functools import partial
import re
from typing import Dict, List

from spectra_lexer.types import polymorph_index, prefix_index
from spectra_lexer.types.dict import ReverseDict
from spectra_lexer.types.search import StripCaseSearchDict

INDEX_BY_PREFIX = use_if_prefix_is = prefix_index()
INDEX_BY_RESOURCE = for_resource = polymorph_index()


class AbstractSearchIndex:
    """ Abstract base class with specific methods for steno search. """

    def search(self, pattern:str, **kwargs) -> List[str]:
        """ Perform a special search for <pattern> and return a list of results. """
        raise NotImplementedError

    def lookup(self, pattern:str, match:str, **kwargs) -> list:
        """ Do a basic lookup and wrap any result in a list if it isn't one. """
        raise NotImplementedError


class AbstractSearchDelegator(AbstractSearchIndex):
    """ Resource search index that offloads actual text search to other indices. """

    def __init__(self):
        """ Wrap all delegation methods in partials for both speed and convenience. """
        for attr in vars(AbstractSearchIndex):
            if not attr.startswith("_"):
                setattr(self, attr, partial(self.delegate, attr))

    def delegate(self, attr:str, *args, **kwargs):
        """ Delegate a search method to a child based on the given parameters. """
        raise NotImplementedError


class ResourceSearchDict(StripCaseSearchDict, AbstractSearchIndex):
    """ Specialized caseless string search dict. No longer strictly Liskov substitutable. """

    STRIP_CHARS = " "

    def __init__(self, *args, **kwargs):
        super().__init__(*args, _strip=self.STRIP_CHARS, **kwargs)

    def search(self, pattern:str, count:int=None, prefix:bool=True, regex:bool=False, **kwargs) -> List[str]:
        """ Perform a special search for <pattern> with the given flags. Return up to <count> matches. """
        if regex:
            try:
                return self.regex_match_keys(pattern, count)
            except re.error:
                return ["REGEX ERROR"]
        if prefix:
            return self.prefix_match_keys(pattern, count)
        if count is not None:
            return self.get_nearby_keys(pattern, count)
        return []

    def lookup(self, pattern:str, match:str, **kwargs) -> list:
        """ Do a basic lookup and wrap the result in a list. """
        if match in self:
            return [self[match]]
        return []


class StenoSearchDict(ResourceSearchDict):

    STRIP_CHARS = " -"  # For translation-based searches, spaces and hyphens should be stripped off each end.


class ReverseStenoSearchDict(ReverseDict, StenoSearchDict):
    """ Composition class for a strip/case search dict over another dict's *values* instead of its keys.
        ReverseDict must be first in the MRO to take the match keyword before a dict constructor eats it. """

    def lookup(self, pattern:str, match:str, **kwargs) -> list:
        """ Reverse dict values are always lists. """
        return self.get(match) or []


@use_if_prefix_is("/")
@for_resource("rules")
class RulesSearchDict(ResourceSearchDict):
    """ A simple search dict for rule search by name when a prefix is added. """

    STRIP_CHARS = " .+-~"  # To search the rules dictionary, prefix and suffix reference symbols should be stripped.


@use_if_prefix_is.default()
@for_resource("translations")
class TranslationSearchDelegator(AbstractSearchDelegator):
    """ A hybrid forward+reverse steno translation dict. Used when nothing else matches. """

    _forward: StenoSearchDict         # Forward translations dict (strokes -> English words).
    _reverse: ReverseStenoSearchDict  # Reverse translations dict (English words -> strokes).

    def __init__(self, d:Dict[str, str]):
        super().__init__()
        self._forward = StenoSearchDict(d)
        self._reverse = ReverseStenoSearchDict(_match=d)

    def delegate(self, attr:str, *args, strokes:bool=False, **kwargs):
        """ The dict to search only depends on the strokes mode. """
        return getattr(self._forward if strokes else self._reverse, attr)(*args, **kwargs)


@use_if_prefix_is("//")
@for_resource("index")
class IndexSearchDelegator(AbstractSearchDelegator):
    """ A resource-heavy index for finding translations that contain a particular steno rule. """

    DELIM: str = ";"  # Delimiter between rule name and translation.

    _index: Dict[str, dict]  # Index dict from which to create subnexus objects for any rule name on demand.

    def __init__(self, d:Dict[str, dict]):
        """ Index search is a two-part search. The first part goes by rule name, and is very precise.
            It is a key to generate translation nexus objects, so only exact matches will work.
            We will be replacing entries, so we must make a shallow copy of the given index dict. """
        super().__init__()
        self._index = dict(d)

    def delegate(self, attr:str, pattern:str="", *args, prefix=False, **kwargs) -> List[str]:
        """ Delegation function for a rule;subpattern index search combo. """
        key, subpattern = (pattern.split(self.DELIM, 1) + [""])[:2]
        d = self._index.get(key)
        if d is not None:
            if not isinstance(d, TranslationSearchDelegator):
                # Search dicts are memory hogs, and users tend to look at many results under the same rule.
                # We generate each search nexus from its index only on demand.
                d = self._index[key] = TranslationSearchDelegator(d)
            # Manually set the search flags to avoid regex search.
            kwargs.update(prefix=prefix, regex=False)
            return getattr(d, attr)(subpattern, *args, **kwargs)
        return []
