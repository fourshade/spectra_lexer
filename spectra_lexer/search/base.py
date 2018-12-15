import re
from typing import Dict, List, Union

from spectra_lexer import SpectraComponent
from spectra_lexer.search.key_search import StringSearchDict
from spectra_lexer.search.steno_search import BidirectionalStenoSearchDict


class SearchEngine(SpectraComponent):

    _dict: BidirectionalStenoSearchDict  # Current search dict (contains both forward and reverse dicts)

    def __init__(self):
        """ Initialize the base dict with the search function and any given arguments. """
        self._dict = BidirectionalStenoSearchDict()

    def engine_commands(self) -> dict:
        """ Individual components must define the signals they respond to and the appropriate callbacks. """
        return {**super().engine_commands(),
                "new_search_dict": self.set_dict,
                "search_lookup":   self.get,
                "search_special":  self.search}

    def set_dict(self, src_dict:Dict[str, str]) -> None:
        """ Create the search dictionary from the raw steno dictionary given. """
        self._dict.clear()
        self._dict.update(src_dict)

    def _get_directional_dict(self, forward) -> StringSearchDict:
        """ Get either the forward or reverse dict for an operation. """
        return self._dict if forward else self._dict.reverse

    def get(self, match, forward=True) -> Union[str, List[str]]:
        """ Perform a simple lookup as with dict.get in the specified direction (forward by default). """
        return self._get_directional_dict(forward).get(match)

    def search(self, pattern:str, count:int=None, forward=True, regex=False) -> List[str]:
        """ Perform a special search in the current direction (for strokes given a translation
            or translations given a stroke) for <pattern> and return a list of up to <count> matches."""
        d = self._get_directional_dict(forward)
        if regex:
            try:
                return d.regex_match_keys(pattern, count)
            except re.error:
                return ["REGEX ERROR"]
        else:
            return d.prefix_match_keys(pattern, count)
