from itertools import repeat
import re
from typing import Callable, Dict, Iterable, List

from .dict import StringSearchDict, ReverseStringSearchDict


def _strip_lower_simfns(strip_chars:str=None) -> Dict[str, Callable]:
    """ Create similarity functions that remove case and strips a user-defined set of symbols.
        Return them as a dict that can be passed straight into search constructors as **kwargs. """
    if strip_chars is None:
        return {}
    # Define string methods and strip characters as default argument locals for speed.
    def simfn(s:str, strip_chars=strip_chars, _strip=str.strip, _lower=str.lower) -> str:
        return _lower(_strip(s, strip_chars))
    # Also define a mapped version for use across a large number of keys.
    # Mapping the built-in string methods separately provides a large speed boost.
    def mapfn(s_iter:Iterable[str], rp_chars=repeat(strip_chars)) -> map:
        return map(str.lower, map(str.strip, s_iter, rp_chars))
    return {"simfn": simfn, "mapfn": mapfn}


class StringSearchDictCollection(Dict[str, StringSearchDict]):
    """ Composite class for similar-key string lookups on one of many dictionaries, including special searches. """

    _global_kwargs: dict  # Global keyword arguments for construction of each child dict.
    _d: StringSearchDict  # Current dict in use for lookups. Must be switched explicitly.

    def __init__(self, *, strip_chars:str=None, **kwargs):
        """ Create an empty collection with the given kwargs as defaults. If strip_chars is given, generate simfns. """
        super().__init__()
        self._global_kwargs = {**_strip_lower_simfns(strip_chars), **kwargs}
        self.use_dict("")

    def new(self, key:str, src_dict:dict=None, *, reverse:bool=False, strip_chars:str=None, **kwargs) -> None:
        """ Create a new string search dictionary (forward or reverse) under the given key using the default simfns.
            New keywords may be given in this method that override the global ones on an individual basis. """
        kwargs = {**self._global_kwargs, **_strip_lower_simfns(strip_chars), **kwargs}
        if reverse:
            self._d = self[key] = ReverseStringSearchDict(match=src_dict, **kwargs)
        else:
            self._d = self[key] = StringSearchDict(src_dict or {}, **kwargs)

    def use_dict(self, key:str) -> None:
        """ Set the current dict to search from. If the key is invalid, use a temporary empty one. """
        self._d = self.get(key) or StringSearchDict()

    def search(self, pattern:str, count:int=None, regex:bool=False) -> List[str]:
        """ Perform a special search for <pattern> with the given dict and mode. Return up to <count> matches. """
        if not regex:
            return self._d.prefix_match_keys(pattern, count)
        try:
            return self._d.regex_match_keys(pattern, count)
        except re.error:
            return ["REGEX ERROR"]

    def get_list(self, match:str) -> List[str]:
        """ Perform a simple lookup as with dict.get. If the results aren't a list, make it one. """
        m_list = self._d.get(match) or []
        if not isinstance(m_list, list):
            m_list = [m_list]
        return m_list
