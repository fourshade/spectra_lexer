from collections import defaultdict
from typing import Callable, Dict, Iterable, List, Tuple

from .parallel import BaseMapper, FilterMapper
from .rules import StenoRule


class IndexMapper(BaseMapper):
    """ Filter mapper with basic integer size control for index creation. """

    MINIMUM_SIZE = 1   # Minimum index size. Below this size, input filters block everything.
    DEFAULT_SIZE = 12  # Default index size. Essentially the maximum word length.
    MAXIMUM_SIZE = 20  # Maximum index size. At this size and above, input filters are disabled.

    SIZE_DESCRIPTIONS = ["size = 1: includes nothing.",
                         "size = 10: fast index with relatively simple words.",
                         "size = 12: average-sized index (default).",
                         "size = 15: slower index with more advanced words.",
                         "size = 20: includes everything."]

    _size: int  # Determines the relative size of a generated index (range 1-20).

    def __init__(self, func:Callable, size:int=DEFAULT_SIZE, *args, **kwargs) -> None:
        """ Generate filters to control index size. Larger translations are excluded with smaller index sizes. """
        self._size = size
        if size < self.MINIMUM_SIZE:
            # If the size is below minimum, it could be a dummy run. Don't run an analysis; just return an empty list.
            self.starmap = lambda iterable: []
            return
        if size >= self.MAXIMUM_SIZE:
            # Remove the overhead of the input filter if we're keeping everything.
            self.filter_in = None
        self.starmap = FilterMapper(func, self.filter_in, self.filter_out, *args, **kwargs).starmap

    def filter_in(self, translation:tuple) -> bool:
        """ Filter function to eliminate larger entries from the index depending on the size factor. """
        return max(map(len, translation)) <= self._size

    def filter_out(self, rule:StenoRule) -> bool:
        """ Filter function to eliminate lexer results that are unmatched or basic rules themselves. """
        return len(rule.rulemap) > 1


class StenoAnalyzer:

    _rules: Dict[str, StenoRule]
    _translations: Iterable[Tuple[str, str]] = ()

    def __init__(self, rules:Dict[str, StenoRule]) -> None:
        self._rules = rules

    def load_translations(self, translations:Iterable) -> None:
        """ Load a set of translations to operate on. """
        self._translations = translations

    def make_rules(self, mapper:BaseMapper) -> List[StenoRule]:
        """ Run the lexer on all translations and return a list of results. """
        return mapper.starmap(self._translations)

    def make_index(self, mapper:BaseMapper) -> Dict[str, dict]:
        """ Run the lexer in parallel on all translations and return a translation index. """
        results = self.make_rules(mapper)
        return self._compile_index(results)

    def _compile_index(self, results:Iterable[StenoRule]) -> Dict[str, dict]:
        """ Using rulemaps, make dicts of all translations that use each built-in rule at the top level. """
        tr_dicts = defaultdict(dict)
        for rs in results:
            keys = rs.keys
            letters = rs.letters
            for item in rs.rulemap:
                tr_dicts[item.rule][keys] = letters
        # Convert the rule keys to strings. Hardcoded and missing rules will map to None.
        rev_rules = {v: k for k, v in self._rules.items()}
        d = {rev_rules.get(k): v for k, v in tr_dicts.items()}
        # Entries with no rule are useless, and None/null is not a valid key in JSON, so toss it.
        if None in d:
            del d[None]
        return d
