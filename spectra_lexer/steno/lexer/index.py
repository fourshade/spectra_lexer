from collections import defaultdict
from typing import Dict, Iterable

from spectra_lexer.steno.rules import StenoRule


class LexerIndexCompiler:
    """ Compiles lexer results into indices for built-in rules and generates filters to control index size. """

    _rev_rules: Dict[StenoRule, str] = {}  # Reverse rules dict for rule -> name translation.

    def set_rev_rules(self, d:dict) -> None:
        """ Set up the reverse rule dict. """
        self._rev_rules = d

    def make_filters(self, size:int) -> tuple:
        """ The parameter <size> determines the relative size of a generated index (range 1-20). """
        def filter_in(translation, max_length=size) -> bool:
            """ Filter function to eliminate larger entries from the index depending on the size factor. """
            return max(map(len, translation)) <= max_length
        def filter_out(rule) -> bool:
            """ Filter function to eliminate lexer results that are unmatched or basic rules themselves. """
            return len(rule.rulemap) > 1
        return (filter_in if size < 20 else None), filter_out

    def compile_results(self, results:Iterable[StenoRule]) -> Dict[str, dict]:
        """ From lexer rulemaps, make dicts of all translations that use each built-in rule at the top level. """
        tr_dicts = defaultdict(dict)
        for rs in results:
            keys = rs.keys
            letters = rs.letters
            for item in rs.rulemap:
                tr_dicts[item.rule][keys] = letters
        # Convert the rule keys to strings. Hardcoded and missing rules will map to None.
        index = {self._rev_rules.get(k): v for k, v in tr_dicts.items()}
        # Entries with no rule are useless, and None is not a valid key in JSON, so toss it.
        if None in index:
            del index[None]
        return index
