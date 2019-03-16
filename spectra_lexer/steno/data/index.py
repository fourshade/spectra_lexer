from typing import Dict, Optional

from spectra_lexer import Component
from spectra_lexer.steno.rules import StenoRule


class IndexManager(Component):
    """ Translation index handler for the Spectra program.
        The structure is a dict of rule objects, each mapped to a string dict of steno translations.
        Simple as it is, the structure is large and requires a lot of CPU load to process. """

    file = Option("cmdline", "index-file", "~/index.json", "JSON index file to load at startup and/or write to.")
    out = Option("cmdline", "index-out", "~/index.json", "Output file name for steno rule -> translation indices.")

    _fwd_rules: Dict[str, StenoRule] = {}  # Forward rules dict for name -> rule translation.
    _rev_rules: Dict[StenoRule, str] = {}  # Reverse rules dict for rule -> name translation.

    @on("new_rules")
    def set_rules(self, d:dict) -> None:
        """ Set up the rule dict in both directions. """
        self._fwd_rules = d
        self._rev_rules = {v: k for (k, v) in d.items()}

    @pipe("start", "new_index")
    @pipe("index_load", "new_index")
    def load(self, filename:str="") -> Optional[Dict[StenoRule, dict]]:
        """ Load an index from disk if one is found. Ignore failures. """
        try:
            d = self.engine_call("file_load", filename or self.file)
        except OSError:
            return None
        # Convert each rule key into its corresponding steno rule object and return the result.
        return _convert_keys(d, self._fwd_rules)

    @pipe("index_save", "file_save")
    def save(self, d:Dict[StenoRule, dict], filename:str="") -> tuple:
        """ Save an index structure into JSON after converting rules back into names.
            Saving should not fail silently, unlike loading. If no save filename is given, use the default. """
        return (filename or self.out), _convert_keys(d, self._rev_rules)


def _convert_keys(d:dict, cdict:dict) -> dict:
    """ Convert the keys of a dict using another mapping, leaving the values alone. """
    new_dict = dict(zip(map(cdict.get, d), d.values()))
    # Hardcoded rules and missing rules end up under the key None after conversion in either direction.
    # These entries are useless, and None is not a valid key in JSON, so toss it.
    if None in new_dict:
        del new_dict[None]
    return new_dict
