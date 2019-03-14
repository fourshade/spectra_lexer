""" Module with special cases of string search dictionaries. """

import re
from itertools import repeat
from typing import Dict, Iterable, List

from .dict import ReverseDict, StringSearchDict
from spectra_lexer.utils import ensure_list


class StripCaseSearchDict(StringSearchDict):
    """ Class that performs string-based searches after stripping symbols and neutralizing case. """

    def __init__(self, d:dict=None, strip_chars:str="", *, strip_fn=str.strip, case_fn=str.lower, **kwargs):
        """ Make similarity functions that remove case and strip a user-defined set of symbols for the constructor. """
        def simfn(s:str, _strip_chars=strip_chars, _strip_fn=strip_fn, _case_fn=case_fn) -> str:
            return _case_fn(_strip_fn(s, _strip_chars))
        # Also define a mapped version for use across a large number of keys.
        # Mapping the built-in string methods separately provides a large speed boost.
        def mapfn(s_iter:Iterable[str]) -> map:
            return map(case_fn, map(strip_fn, s_iter, repeat(strip_chars)))
        super().__init__(d or {}, simfn=simfn, mapfn=mapfn, **kwargs)

    def search(self, pattern:str, count:int, regex:bool) -> List[str]:
        """ Perform a special search for <pattern> with the current dict. Return up to <count> matches. """
        if regex:
            try:
                return self.regex_match_keys(pattern, count)
            except re.error:
                return ["REGEX ERROR"]
        return self.prefix_match_keys(pattern, count)

    def get_list(self, match:str) -> List[str]:
        """ Perform a simple lookup on a dict. If the results aren't a list, make it one. """
        return ensure_list(self.get(match) or [])


class ReverseStripCaseSearchDict(ReverseDict, StripCaseSearchDict):

    def __init__(self, d:Dict[str, str], *args, **kwargs):
        """ For a reverse dict, we only want to match the forward dict and pass all other arguments along. """
        super().__init__(None, *args, match=d, **kwargs)
