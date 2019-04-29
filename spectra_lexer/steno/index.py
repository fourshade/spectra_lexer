from typing import Dict, Optional

from spectra_lexer.core import Component
from spectra_lexer.file import JSON


class IndexManager(Component):
    """ Translation index handler for the Spectra program.
        The structure is a dict of rule names, each mapped to a string dict of steno translations.
        Simple as it is, the structure is large and requires a lot of CPU load to process. """

    file = resource("cmdline:index-file", "~/index.json", desc="JSON index file to load on startup and/or write to.")
    out = resource("cmdline:index-out", "~/index.json", desc="Output file name for steno rule -> translation indices.")

    @on("init:index")
    def start(self, *dummy) -> Optional[Dict[str, dict]]:
        return self.load()

    @on("index_load")
    @pipe_to("res:index")
    def load(self, filename:str="") -> Optional[Dict[str, dict]]:
        """ Load an index from disk if one is found. Ask the user to make one on failure. """
        try:
            return JSON.load(filename or self.file)
        except OSError:
            self.engine_call("index_not_found")
            return

    @on("index_save")
    def save(self, d:Dict[str, dict], filename:str="") -> None:
        """ Save an index structure directly into JSON. Sort all rules and translations by key.
            Saving should not fail silently, unlike loading. If no save filename is given, use the default. """
        JSON.save(filename or self.out, d, sort_keys=True)
