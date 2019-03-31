from collections import defaultdict
from typing import Dict, Iterable, Optional

from spectra_lexer import Component
from spectra_lexer.file import JSON
from spectra_lexer.steno.rules import StenoRule
from spectra_lexer.steno.system import StenoSystem


class IndexManager(Component):
    """ Translation index handler for the Spectra program.
        The structure is a dict of rule names, each mapped to a string dict of steno translations.
        Simple as it is, the structure is large and requires a lot of CPU load to process. """

    file = Resource("cmdline", "index-file", "~/index.json", "JSON index file to load at startup and/or write to.")
    out = Resource("cmdline", "index-out", "~/index.json", "Output file name for steno rule -> translation indices.")
    size = Resource("cmdline", "index-size", 12, "Determines the relative size of a generated index (range 1-20).")

    _rev_rules: Dict[StenoRule, str] = {}  # Reverse rules dict for rule -> name translation.

    @on("set_system")
    def set_system(self, system:StenoSystem) -> None:
        """ Set up the reverse rule dict. """
        self._rev_rules = system.rev_rules

    @on("load_dicts", pipe_to="set_dict_index")
    @on("index_load", pipe_to="set_dict_index")
    def load(self, filename:str="") -> Optional[Dict[str, dict]]:
        """ Load an index from disk if one is found. Ask the user to make one on failure. """
        try:
            return JSON.load(filename or self.file)
        except OSError:
            self.engine_call("index_not_found")
            return

    @on("index_save")
    def save(self, d:Dict[str, dict], filename:str="") -> None:
        """ Save an index structure directly into JSON.
            Saving should not fail silently, unlike loading. If no save filename is given, use the default. """
        JSON.save(filename or self.out, d)

    @on("index_generate", pipe_to="set_dict_index")
    def generate(self, translations:Iterable=None, *, size:int=None, save=True) -> Dict[str, dict]:
        """ Generate a set of rules from translations using the lexer and compare them to the built-in rules.
            Make a index for each built-in rule containing a dict of every lexer translation that used it. """
        if isinstance(translations, dict):
            translations = translations.items()
        if size is None:
            size = self.size
        filter_in, filter_out = self._make_filters(size)
        results = self.engine_call("lexer_query_all", translations, filter_in, filter_out, save=False)
        translation_lists = self._count_rules(results)
        index = self._sort_translations(translation_lists)
        if save:
            self.engine_call("index_save", index)
        return index

    def _make_filters(self, size:int):
        def filter_in(translation, max_length=size) -> bool:
            """ Filter function to eliminate larger entries from the index depending on the size factor. """
            return max(map(len, translation)) <= max_length
        def filter_out(rule) -> bool:
            """ Filter function to eliminate lexer results that are unmatched or basic rules themselves. """
            return len(rule.rulemap) > 1
        return (filter_in if size < 20 else None), filter_out

    def _count_rules(self, results:Iterable[StenoRule]) -> Dict[str, list]:
        """ From the lexer rulemaps, make lists of all translations that use each built-in rule at the top level. """
        rulecounter = defaultdict(list)
        for rs in results:
            for item in rs.rulemap:
                rule = item.rule
                rulecounter[rule].append((rs.keys, rs.letters))
        return rulecounter

    def _sort_translations(self, translation_lists:Dict[str, list]) -> Dict[str, dict]:
        """ From the dict of lists, sort all translations in each list and convert the rule keys to strings.
            After sorting, turn each list into a dict. The dicts will preserve this ordering when saved to disk. """
        keys = map(self._rev_rules.get, translation_lists.keys())
        values = map(dict, map(sorted, translation_lists.values()))
        index = dict(zip(keys, values))
        # Hardcoded rules and missing rules end up under the key None after conversion.
        # These entries are useless, and None is not a valid key in JSON, so toss it.
        if None in index:
            del index[None]
        return index
