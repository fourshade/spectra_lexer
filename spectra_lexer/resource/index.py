from collections import defaultdict
import random
from typing import Dict, Iterable, List, Tuple

from .rules import StenoRule
from .translations import TranslationsDictionary
from spectra_lexer.types.codec import JSONDict


class StenoIndex(JSONDict):
    """ A resource-heavy index dict-of-dicts for finding translations that contain a particular steno rule.
        Index search is a two-part search. The first part goes by rule name, and is very precise.
        It is a key to generate translation dict objects, so only exact matches will work. """

    def search(self, index_key:str, pattern:str, **kwargs) -> List[str]:
        d = self.get(index_key)
        if not d:
            return []
        if not isinstance(d, TranslationsDictionary):
            # Search indices are memory hogs, and users tend to look at many results under the same rule.
            # We convert each dict to a full translations search index only on demand.
            d = self[index_key] = TranslationsDictionary(d)
        # Manually set the search flags to avoid regex search.
        kwargs["regex"] = False
        return d.search(pattern, prefix=False, **kwargs)

    def lookup(self, index_key:str, match:str, **kwargs) -> List[str]:
        return self[index_key].lookup(match, **kwargs)

    def find_example(self, index_key:str) -> Tuple[str, str]:
        """ Given a rule/index key by name, return one translation using it at random. """
        d = self.get(index_key)
        if not d:
            return "", ""
        k = random.choice(list(d))
        return k, d[k]

    @classmethod
    def compile(cls, rules:Iterable[StenoRule], rev_rules:Dict[StenoRule, str]):
        """ Using rulemaps, make dicts of all translations that use each built-in rule at the top level. """
        tr_dicts = defaultdict(dict)
        for rs in rules:
            keys = rs.keys
            letters = rs.letters
            for item in rs.rulemap:
                tr_dicts[item.rule][keys] = letters
        # Convert the rule keys to strings. Hardcoded and missing rules will map to None.
        d = {rev_rules.get(k): v for k, v in tr_dicts.items()}
        # Entries with no rule are useless, and None/null is not a valid key in JSON, so toss it.
        if None in d:
            del d[None]
        return cls(d)
