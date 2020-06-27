from itertools import islice
from operator import methodcaller
import re
from typing import Callable, Dict, Iterable, List, TypeVar

from .similar import SimilarKeyMap

V = TypeVar("V")
StringIter = Iterable[str]
StringList = List[str]
MultiStringDict = Dict[str, StringList]


class RegexError(Exception):
    """ Raised if there's a syntax error in a regex search. """


def _regex_matcher(pattern:str) -> Callable:
    """ Compile a regular expression pattern and return a match predicate function. """
    try:
        return re.compile(pattern).match
    except re.error as e:
        raise RegexError(pattern + " is not a valid regular expression.") from e


class StringKeyMap(SimilarKeyMap[str, V]):
    """ A similar-key mapping with special search methods for string keys.
        In order for the standard optimizations involving literal prefixes to work, the similarity function must
        not change the relative order of characters (i.e. changing case is fine, reversing the string is not.) """

    # Regex matcher for ASCII characters without special regex behavior when used at the start of a pattern.
    # Will always return at least the empty string (which is a prefix of everything).
    _LITERAL_PREFIX_MATCH = _regex_matcher(r'[\w \"#%\',\-:;<=>@`~]*')

    def prefix_match_keys(self, prefix:str, count:int=None) -> StringList:
        """ Return a list of keys where the simkey starts with <prefix>, up to <count>. """
        sk_start = self._simfn(prefix)
        if not sk_start:
            # If the prefix is empty after transformation, it could possibly match anything.
            items = self._list if count is None else self._list[:count]
        else:
            # All matches will be found in the sort order between the prefix itself (inclusive) and
            # the prefix with one added to the ordinal of its final character (exclusive).
            sk_end = sk_start[:-1] + chr(ord(sk_start[-1]) + 1)
            idx_start = self._index_left(sk_start)
            idx_end = self._index_left(sk_end)
            if count is not None:
                idx_end = min(idx_end, idx_start + count)
            items = self._list[idx_start:idx_end]
        return [item[1] for item in items]

    def regex_match_keys(self, pattern:str, count:int=None) -> StringList:
        """ Return a list of at most <count> keys that match the regex <pattern> from the start. """
        # First, figure out how much of the pattern string from the start is literal (no regex special characters).
        literal_prefix = self._LITERAL_PREFIX_MATCH(pattern).group()
        # If all matches must start with a certain literal prefix, we can narrow the range of our search.
        keys = self.prefix_match_keys(literal_prefix, count=None)
        if not keys:
            return []
        # If the prefix and pattern are equal, we have a complete literal string. Regex is not necessary.
        # Just do an *exact* prefix match in that case. Otherwise, compile the regular expression.
        if literal_prefix == pattern:
            match_op = methodcaller("startswith", pattern)
        else:
            match_op = _regex_matcher(pattern)
        # Run the match filter until <count> entries have been produced (if None, search the entire key list).
        return list(islice(filter(match_op, keys), count))


class StringMap(StringKeyMap[str]):
    """ Searchable one-to-one string mapping. """

    def lookup(self, keys:StringIter) -> MultiStringDict:
        """ Forward mapping values are strings; wrap each one in a list. """
        d = self._d
        return {k: [d[k]] for k in keys}


class MultiStringMap(StringKeyMap[StringList]):
    """ Searchable one-to-many string mapping. """

    def lookup(self, keys:StringIter) -> MultiStringDict:
        """ Reverse mapping values are lists; copy them so the caller can't mutate the originals.
            [*unpacking] seems to be the fastest way to copy large numbers of small lists. """
        d = self._d
        return {k: [*d[k]] for k in keys}
