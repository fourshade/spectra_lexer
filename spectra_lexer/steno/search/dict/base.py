""" Base module for special dictionaries used in search. """

import re
from itertools import repeat
from typing import Iterable, List

from .reverse import ReverseDict
from .search import StringSearchDict


class StripCaseSearchDict(StringSearchDict):
    """ Class that performs string-based searches after stripping symbols and neutralizing case. """

    def __init__(self, *args, strip_chars:str=None, **kwargs):
        """ Make similarity functions that remove case and strip a user-defined set of symbols for the constructor. """
        if strip_chars is not None:
            def simfn(s:str, _strip_chars=strip_chars, _strip_fn=str.strip, _case_fn=str.lower) -> str:
                return _case_fn(_strip_fn(s, _strip_chars))
            # Also define a mapped version for use across a large number of keys.
            # Mapping the built-in string methods separately provides a large speed boost.
            def mapfn(s_iter:Iterable[str]) -> map:
                return map(str.lower, map(str.strip, s_iter, repeat(strip_chars)))
            kwargs.update(simfn=simfn, mapfn=mapfn)
        super().__init__(*args, **kwargs)

    def search(self, pattern:str, count:int, *, prefix:bool=True, regex:bool=False) -> List[str]:
        """ Perform a special search for <pattern> with the given flags. Return up to <count> matches. """
        if prefix:
            if regex:
                try:
                    return self.regex_match_keys(pattern, count)
                except re.error:
                    return ["REGEX ERROR"]
            return self.prefix_match_keys(pattern, count)
        return self.get_nearby_keys(pattern, count)

    def lookup(self, match:str) -> list:
        """ Do a basic lookup and wrap the result in a list. """
        if match in self:
            return [self[match]]
        return []


class ReverseStripCaseSearchDict(ReverseDict, StripCaseSearchDict):
    """ Composition class for a strip/case search dict over another dict's *values* instead of its keys.
        ReverseDict must be first in the MRO to take the match keyword before a dict constructor eats it. """

    def lookup(self, match:str) -> list:
        """ Reverse dict values are always lists. """
        return self.get(match) or []
