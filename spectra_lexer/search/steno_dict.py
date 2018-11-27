""" Module for steno-specific key-search, reverse, and composite dicts. """

import re
from typing import Dict, List

from spectra_lexer.search.search_dict import StringSearchDict, ReverseDict

# Hard limit on the number of matches returned by a special search.
_MATCH_LIMIT = 100


class _StenoSearchDict(StringSearchDict):
    """
    String-based similar-key searchable dict for steno translations where key:value = strokes:translation.
    For the similarity function, remove case and strip a user-defined set of symbols.
    This should work well for either ordering of strokes <-> translation.
    """

    def __init__(self, *args, strip_chars:str=' ', **kwargs):
        """ Initialize the base dict with the search function and any given arguments. """
        # Define string methods as function closure locals for speed.
        strip = str.strip
        lower = str.lower
        def simfn(s:str) -> str:
            return lower(strip(s, strip_chars))
        super().__init__(*args, simfn=simfn, **kwargs)


class _ReverseStenoSearchDict(_StenoSearchDict, ReverseDict):
    """
    String-based similar-key searchable dict created by reversing a normal steno dict.
    It maps translations to lists of stroke sequences that will produce them.
    """

    def __init__(self, *args, **kwargs):
        """ Use the positional argument (if given, and only one) as a source forward dict. """
        super().__init__(**kwargs)
        if args:
            assert len(args) == 1
            self.match_forward(args[0])


class CompositeSearchDictionary:
    """ Composite dict class for ordinary lookups, reverse lookups, and special searches in both directions. """

    _forward: _StenoSearchDict         # Forward search dict (strokes -> translations)
    _reverse: _ReverseStenoSearchDict  # Reverse search dict (translations -> strokes)
    mode_strokes: bool = False         # If True, use the forward dict, else use the reverse dict.
    mode_regex: bool = False           # If True, treat search text input as a regular expression.

    def __init__(self, src_dict:Dict[str, str]):
        """ Create the necessary search dictionaries from the raw steno dictionary given.
            For stroke searches (forward), hyphens should be stripped off the front (as well as spaces).
            For translation searches (reverse), just stripping spaces should be fine. """
        self._forward = _StenoSearchDict(src_dict, strip_chars=' -')
        self._reverse = _ReverseStenoSearchDict(src_dict, strip_chars=' ')

    def __bool__(self):
        return bool(self._forward)

    def __getattr__(self, attr):
        """ Any attribute not specified here gets lookup delegated to a dict based on the current mode. """
        d = self._forward if self.mode_strokes else self._reverse
        return getattr(d, attr)

    def search(self, pattern:str, count:int=_MATCH_LIMIT) -> List[str]:
        """
        Perform a special search in the current direction (for strokes given a translation
        or translations given a stroke) and return a list of matches.

        pattern: Text pattern to match.
        count: Maximum number of matches to return.
        """
        if self.mode_regex:
            try:
                return self.regex_match_keys(pattern, count)
            except re.error:
                return ["REGEX ERROR"]
        else:
            return self.prefix_match_keys(pattern, count)
