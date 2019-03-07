from itertools import chain
from typing import Dict

from spectra_lexer.core import TranslationsManager
from spectra_lexer.plover.compat import join_strokes, PloverStenoDictCollection


class PloverTranslationsManager(TranslationsManager):
    """ Translation parser for the Plover plugin. Plover's data structures behave *almost* like dicts but not quite. """

    @on("start")
    def start(self, **opts) -> None:
        """ Since plugin mode uses dictionaries from Plover's memory, translations should not be loaded from disk. """
        return None

    @pipe("plover_load_dicts", "new_translations")
    def load_dicts(self, steno_dc:PloverStenoDictCollection) -> Dict[str, str]:
        """ When usable Plover dictionaries become available, parse their items into a single string dict for search.
            Plover dictionaries are not proper Python dicts and cannot be handled as such.
            They only have a subset of the normal dict methods. The fastest of these is d.items(). """
        finished_dict = {}
        for d in steno_dc.dicts:
            if d and d.enabled:
                if isinstance(next(iter(d.items())), tuple):
                    # If strokes are in tuple form, they must be joined into strings.
                    # The fastest method found in profiling uses a chained alternating iterator.
                    kv_alt = chain.from_iterable(d.items())
                    finished_dict.update(zip(map(join_strokes, kv_alt), kv_alt))
                else:
                    finished_dict.update(d.items())
        return finished_dict
