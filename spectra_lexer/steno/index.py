from collections import defaultdict
from typing import List

from .keys import KeyLayout
from .lexer import StenoLexer
from .parallel import ParallelMapper
from .search import ExamplesDict, TranslationsDict


class TranslationSizeFilter:
    """ Filter for translations based on their size.  """

    MINIMUM_SIZE = 1   # Below this size, the filter blocks everything.
    SMALL_SIZE = 10
    MEDIUM_SIZE = 12
    LARGE_SIZE = 15
    MAXIMUM_SIZE = 20  # At this size and above, the filter is disabled.

    def __init__(self, size:int=None) -> None:
        self._size = size or self.MEDIUM_SIZE  # Maximum allowed length of any string in a translation.

    def filter(self, translations:TranslationsDict) -> TranslationsDict:
        """ Return a new dict with <translations> filtered according to the required maximum size. """
        size = self._size
        if size < self.MINIMUM_SIZE:
            # If the size is below minimum, it could be a dummy run. Keep nothing.
            return {}
        elif size >= self.MAXIMUM_SIZE:
            # If the size is maximum, filtering is unnecessary. Keep everything.
            return dict(translations)
        # Eliminate long translations depending on the size factor.
        return {keys: letters for keys, letters in translations.items()
                if len(keys) <= size and len(letters) <= size}


class IndexFactory:
    """ Factory for an examples index using multiprocessing with the lexer. """

    def __init__(self, layout:KeyLayout, lexer:StenoLexer) -> None:
        self._layout = layout  # Converts between user RTFCRE steno strings and s-keys.
        self._lexer = lexer

    def make_index(self, translations:TranslationsDict, *args, **kwargs) -> ExamplesDict:
        """ Run the lexer on all <translations> with an input filter and look at the top-level rule names.
            Make a index containing a dict for each built-in rule with every translation that used it. """
        tr_filter = TranslationSizeFilter(*args)
        translations = tr_filter.filter(translations)
        mapper = ParallelMapper(self._query, **kwargs)
        index = defaultdict(dict)
        for keys, letters, *names in mapper.starmap(translations.items()):
            for name in names:
                index[name][keys] = letters
        return index

    def _query(self, keys:str, letters:str) -> List[str]:
        """ Make a lexer query and return the rule names in a list with its matching keys and letters.
            This is required for parallel operations where results may be returned out of order. """
        skeys = self._layout.from_rtfcre(keys)
        result = self._lexer.query(skeys, letters)
        data = [keys, letters]
        # Only fully matched translations should have rules recorded in the index.
        if not result.unmatched_skeys():
            data += result.rule_ids()
        return data
