""" Module with instances and groupings of specialized string search dictionaries. """

import re
from typing import List

from .search import StripCaseSearchDict
from spectra_lexer.types.codec import JSONDict
from spectra_lexer.resource.search import ReverseDict


class _ReverseSearchDict(ReverseDict, StripCaseSearchDict):
    """ Composition class for a strip/case search dict over another dict's *values* instead of its keys.
        ReverseDict must be first in the MRO to take the match keyword before a dict constructor eats it. """


class TranslationsDictionary(JSONDict, StripCaseSearchDict):
    """ A hybrid forward+reverse steno translation dict. Must also behave as a normal dict.
        The base object is the forward translations dict (strokes -> English words). """

    STRIP_CHARS = " -"  # For translation-based searches, spaces and hyphens should be stripped off each end.

    _reverse: _ReverseSearchDict  # Reverse translations dict (English words -> strokes).

    def __init__(self, *args, **kwargs):
        super().__init__(*args, _strip=self.STRIP_CHARS, **kwargs)
        self._reverse = _ReverseSearchDict(_match=self, _strip=self.STRIP_CHARS)

    def search(self, pattern:str, count:int=None, strokes:bool=False, prefix:bool=True, regex:bool=False) -> List[str]:
        """ Perform a special search for <pattern> with the given flags. Return up to <count> matches.
            If <count> is None, perform a normal lookup instead. The dict only depends on the strokes mode. """
        d = self if strokes else self._reverse
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
