from collections import defaultdict
import re
from typing import Callable, Dict, List, Mapping, TypeVar, Union

from spectra_lexer.search.search_dict import StringSearchDict

KT = TypeVar("KT")  # Key type.
VT = TypeVar("VT")  # Value type.


class ReverseDict(Dict[VT, List[KT]]):
    """
    A reverse dictionary. Inverts a mapping from (key: value) to (value: [keys]).

    Since normal dictionaries can have multiple keys that map to the same value (many-to-one),
    reverse dictionaries must necessarily be some sort of one-to-many mapping.
    This means each entry must be a list. This class adds methods that manage those lists.

    Naming conventions are reversed - in a reverse dictionary, we look up a value to get a list
    of keys that would map to it in the forward dictionary.
    """

    def __init__(self, *args, match:dict=None, **kwargs):
        """ Use the keyword argument (if given) as a source forward dict. """
        super().__init__(*args, **kwargs)
        if match is not None:
            self.match_forward(match)

    def append_key(self, v:VT, k:KT) -> None:
        """ Append the key <k> to the list located under the value <v>.
            Create a new list with that key if the value doesn't exist yet. """
        if v in self:
            self[v].append(k)
        else:
            self[v] = [k]

    def remove_key(self, v:VT, k:KT) -> None:
        """ Remove the key <k> from the list located under the value <v>. The key must exist.
            If it was the last key in the list, remove the dictionary entry entirely. """
        self[v].remove(k)
        if not self[v]:
            del self[v]

    def match_forward(self, fdict:Mapping[KT,VT]) -> None:
        """ Make this dict into the reverse of the given forward dict by rebuilding all of the lists.
            It is a fast way to populate a reverse dict from scratch after creation. """
        self.clear()
        rdict = defaultdict(list)
        list_append = list.append
        for (k, v) in fdict.items():
            list_append(rdict[v], k)
        self.update(rdict)


class ReverseStringSearchDict(ReverseDict, StringSearchDict):
    """ Simple inheritance composition of a string-search dict that inverts some other mapping. """


def _strip_lower_simfn(strip_chars:str=' ') -> Callable[[str],str]:
    """ Create a similarity function that removes case and strips a user-defined set of symbols.
        This should work well for search with either ordering of strokes <-> translation. """
    # Define string methods and strip characters as default argument locals for speed.
    def simfn(s:str, strip_chars=strip_chars, _strip=str.strip, _lower=str.lower) -> str:
        return _lower(_strip(s, strip_chars))
    return simfn


class StenoSearchDictionary:
    """ Composite class for steno translation lookups in both directions, including special searches. """

    forward: StringSearchDict         # Forward search dict (strokes -> translations)
    reverse: ReverseStringSearchDict  # Reverse search dict (translations -> strokes)

    def __init__(self, raw_dict:Dict[str,str]=None):
        """ Create both forward and reverse search dictionaries with specific characters stripped. """
        if raw_dict is None:
            raw_dict = {}
        # For stroke searches, hyphens should be stripped off the front (as well as spaces).
        self.forward = StringSearchDict(raw_dict, simfn=_strip_lower_simfn(' -'))
        # For translation searches, just stripping spaces works well enough.
        self.reverse = ReverseStringSearchDict(match=raw_dict, simfn=_strip_lower_simfn(' '))

    def get(self, match:str, from_dict:str="forward") -> Union[str,List[str]]:
        """ Perform a simple lookup as with dict.get. """
        return getattr(self, from_dict).get(match)

    def search(self, pattern:str, count:int=None, from_dict:str="forward", regex:bool=False) -> List[str]:
        """ Perform a special search for <pattern> with the given dict and mode. Return up to <count> matches. """
        d = getattr(self, from_dict)
        if regex:
            try:
                return d.regex_match_keys(pattern, count)
            except re.error:
                return ["REGEX ERROR"]
        else:
            return d.prefix_match_keys(pattern, count)
