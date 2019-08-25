import random
from typing import List

from .translations import TranslationsDictionary


class StenoIndex(dict):
    """ A resource-heavy index dict-of-dicts for finding translations that contain a particular steno rule.
        Index search is a two-part search. The first part goes by rule name; only exact matches will work. """

    def search(self, index_key:str, pattern:str, **kwargs) -> List[str]:
        """ Translation search dicts are memory hogs, and users tend to look at many results under the same rule.
            Convert native dicts (from JSON) to full-featured search dicts only on demand. """
        d = self.get(index_key)
        if not d:
            return []
        if not isinstance(d, TranslationsDictionary):
            d = self[index_key] = TranslationsDictionary(d)
        # Manually set the search flags.
        kwargs.update(prefix=False, regex=False)
        return d.search(pattern, **kwargs)

    def find_example(self, index_key:str, strokes:bool=False) -> str:
        """ Given a rule/index key by name, return one translation using it at random. """
        d = self.get(index_key) or {"": ""}
        k = random.choice(list(d))
        return k if strokes else d[k]

    def __repr__(self) -> str:
        """ Recursive reprs on index objects are deadly. Only show the first level with item counts. """
        item_counts = {k: f"{len(self[k])} items" for k in self}
        return f"<{type(self).__name__}: {item_counts!r}>"
