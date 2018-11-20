import re
from typing import Dict, List

from spectra_lexer.search.dict import ReverseDict, StringSearchDict

# Hard limit on the number of words returned by a search.
WORD_SEARCH_LIMIT = 100


class _StenoSearchDict(StringSearchDict):
    """ String-based similar-key searchable dict for steno translations
        where key:value = strokes:translation. For the similarity function,
        remove case and strip a user-defined set of symbols. """

    def __init__(self, *args, strip_chars:str=' ', **kwargs):
        """ Initialize the base dict with the search function and any given arguments. """
        # Define string methods as function closure locals for speed.
        strip = str.strip
        lower = str.lower
        def simfn(s:str) -> str:
            return lower(strip(s, strip_chars))
        super().__init__(*args, simfn=simfn, **kwargs)


class _ReverseStenoSearchDict(_StenoSearchDict, ReverseDict):
    """ String-based similar-key searchable dict created by reversing a normal steno dict.
        It maps translations to lists of stroke sequences that will produce them. """

    def __init__(self, *args, **kwargs):
        """ Use the positional argument (if given, and only one) as a source forward dict. """
        super().__init__(**kwargs)
        if args:
            assert len(args) == 1
            self.match_forward(args[0])


class SearchEngine:
    """ Main search class for finding strokes and translations that are similar to one another. """

    _fdict: _StenoSearchDict         # Forward search dict (strokes -> translations)
    _rdict: _ReverseStenoSearchDict  # Reverse search dict (translations -> strokes)

    def __init__(self):
        self.set_dict({})

    def __bool__(self):
        """ Truth value is the same as (either of) its dicts: False if empty, True otherwise. """
        return bool(self._fdict)

    def set_dict(self, src_dict:Dict[str, str]):
        """ Create the necessary search dictionaries from the raw steno dictionary given. """
        self._fdict = _StenoSearchDict(src_dict)
        self._rdict = _ReverseStenoSearchDict(src_dict)
        # Direct membership test and lookup methods
        self.get_translation = self._fdict.get
        self.get_strokes = self._rdict.get

    def search(self, pattern:str, reverse:bool=False, regex:bool=False, count:int=WORD_SEARCH_LIMIT) -> List[str]:
        """
        Perform a special search in either direction (for strokes given a translation
        or translations given a stroke) and return a list of matches.

        pattern: Text pattern to match.
        reverse: False = search for translations given a stroke.
                 True = search for strokes given a translation.
        regex: False = case-insensitive prefix matches.
               True = case-sensitive regex matches.
        count: Maximum number of search results to return.
        """
        d = self._rdict if reverse else self._fdict
        if regex:
            try:
                return d.regex_match_keys(pattern, count)
            except re.error:
                return ["REGEX ERROR"]
        else:
            return d.prefix_match_keys(pattern, count)
