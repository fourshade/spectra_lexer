""" Module with instances and groupings of specialized string search dictionaries. """

import re
from typing import List

from spectra_lexer.types.codec import JSONDict
from spectra_lexer.types.dict import ReverseDict
from spectra_lexer.types.search import StripCaseSearchDict


class _StenoSearchDict(StripCaseSearchDict):
    """ Specialized caseless steno string search dict. No longer strictly Liskov substitutable. """

    STRIP_CHARS = " -"  # For translation-based searches, spaces and hyphens should be stripped off each end.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, _strip=self.STRIP_CHARS, **kwargs)

    def search(self, pattern:str, count:int=None, prefix:bool=True, regex:bool=False) -> List[str]:
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

    def lookup(self, match:str) -> List[str]:
        """ Do a basic lookup and wrap the result in a list. """
        if match in self:
            return [self[match]]
        return []


class _ReverseStenoSearchDict(ReverseDict, _StenoSearchDict):
    """ Composition class for a strip/case search dict over another dict's *values* instead of its keys.
        ReverseDict must be first in the MRO to take the match keyword before a dict constructor eats it. """

    def lookup(self, match:str) -> List[str]:
        """ Reverse dict values are always lists. """
        return self.get(match) or []


class TranslationsDictionary(JSONDict, _StenoSearchDict):
    """ A hybrid forward+reverse steno translation dict. Must also behave as a normal dict.
        The base object is the forward translations dict (strokes -> English words). """

    _reverse: _ReverseStenoSearchDict  # Reverse translations dict (English words -> strokes).

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._reverse = _ReverseStenoSearchDict(_match=self)

    def search(self, pattern:str, strokes:bool=False, **kwargs) -> List[str]:
        return self._get_dict(strokes).search(pattern, **kwargs)

    def lookup(self, match:str, strokes:bool=False, **kwargs) -> List[str]:
        return self._get_dict(strokes).lookup(match)

    def _get_dict(self, strokes:bool) -> _StenoSearchDict:
        """ The dict to search only depends on the strokes mode. """
        return super() if strokes else self._reverse
