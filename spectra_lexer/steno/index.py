from typing import Dict

from spectra_lexer.core import Component
from spectra_lexer.file import JSON


class IndexManager(Component):
    """ Translation index handler for the Spectra program.
        The structure is a dict of rule names, each mapped to a string dict of steno translations.
        Simple as it is, the structure is large and requires a lot of CPU load to process. """

    file = resource("cmdline:index-file", "~/index.json", desc="JSON index file to load on startup and/or write to.")
    out = resource("cmdline:index-out", "~/index.json", desc="Output file name for steno rule -> translation indices.")

    @init("index")
    def start(self, *dummy) -> None:
        self.load()

    @on("index_load")
    def load(self, filename:str="") -> Dict[str, dict]:
        """ Load an index from disk if one is found. Ask the user to make one on failure. """
        d = {}
        try:
            d = JSON.load(filename or self.file)
            self._update(d)
        except OSError:
            self.engine_call("index_not_found")
        return d

    @on("index_save")
    def save(self, d:Dict[str, dict], filename:str="") -> None:
        """ Save an index structure directly into JSON. Sort all rules and translations by key and set them active.
            Saving should not fail silently, unlike loading. If no save filename is given, use the default. """
        JSON.save(filename or self.out, d, sort_keys=True)
        self._update(d)

    def _update(self, d:Dict[str, dict]) -> None:
        """ Update the active index on save or load. """
        self.engine_call("res:index", d)
