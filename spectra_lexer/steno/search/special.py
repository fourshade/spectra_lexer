""" Module with special cases of string search dictionaries. """

import re
from itertools import repeat
from typing import Dict, Iterable, List, Optional

from .dict import ReverseDict, StringSearchDict


class StripStringSearchDict(StringSearchDict):
    """ Class that could be one of many types of dictionaries based on characters in the input. """

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
        m_list = self.get(match) or []
        if not isinstance(m_list, list):
            m_list = [m_list]
        return m_list


class StenoSearchDict(StripStringSearchDict):

    def command(self, match:str, mapping:object) -> Optional[tuple]:
        """ Return an engine command (or not) for the given items. Neither may be empty by any measure. """
        if match and mapping:
            multi_match = isinstance(match, list)
            multi_mapping = isinstance(mapping, list)
            if multi_match or multi_mapping:
                # If there is more than one of either input, make a product query to select the best combination.
                match = match if multi_match else [match]
                mapping = mapping if multi_mapping else [mapping]
                return "lexer_query_product", match, mapping
            # By default, the items are assumed to be direct lexer input. """
            return "lexer_query", match, mapping


class ReverseStenoSearchDict(ReverseDict, StenoSearchDict):

    def __init__(self, d:Dict[str, str], *args, **kwargs):
        """ For a reverse dict, we only want to match the forward dict and pass all other arguments along. """
        super().__init__(None, *args, match=d, **kwargs)

    def command(self, match:str, mapping:str) -> tuple:
        """ The order of strokes/word in the lexer command is reversed for a reverse dict. """
        return super().command(mapping, match)
