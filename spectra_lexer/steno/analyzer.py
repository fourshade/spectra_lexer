from functools import lru_cache

from .base import LX
from .graph import StenoGraph
from spectra_lexer.resource import RulesDictionary, StenoIndex, StenoRule

# Default size of generated indices (maximum word size).
_DEFAULT_INDEX_SIZE = 12


class StenoAnalyzer(LX):
    """ The primary batch steno analysis engine. Queries the lexer in bulk and creates indices. """

    def LXAnalyzerMakeRules(self, *args, **kwargs) -> RulesDictionary:
        """ The original rules are also used for dereferencing on encode. """
        results = self.LXQueryAll(*args, **kwargs)
        return RulesDictionary(zip(map(str, results), results), **self.RULES)

    def LXAnalyzerMakeIndex(self, size:int=_DEFAULT_INDEX_SIZE) -> StenoIndex:
        """ Generate filters to control index size. Larger words are excluded with smaller index sizes.
            The parameter <size> determines the relative size of a generated index (range 1-20). """
        def filter_in(translation:tuple, max_length:int=size) -> bool:
            """ Filter function to eliminate larger entries from the index depending on the size factor. """
            return max(map(len, translation)) <= max_length
        def filter_out(rule:StenoRule) -> bool:
            """ Filter function to eliminate lexer results that are unmatched or basic rules themselves. """
            return len(rule.rulemap) > 1
        # Only keep results with all keys matched to reduce garbage.
        results = self.LXQueryAll(filter_in if size < 20 else None, filter_out, need_all_keys=True)
        return StenoIndex.compile(results, self.RULES.inverse)

    @lru_cache(maxsize=256)
    def LXGraphGenerate(self, rule:StenoRule, recursive:bool=True, compressed:bool=True) -> StenoGraph:
        """ Generate a graph object. This isn't cheap, so the most recent ones are cached. """
        layout = self.LAYOUT
        return StenoGraph(rule, layout.SEP, layout.SPLIT, recursive, compressed)
