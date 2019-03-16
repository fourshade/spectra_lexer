from typing import Dict, Optional

from spectra_lexer import Component


class IndexManager(Component):
    """ Translation index handler for the Spectra program.
        The structure is a dict of rule names, each mapped to a string dict of steno translations.
        Simple as it is, the structure is large and requires a lot of CPU load to process. """

    file = Option("cmdline", "index-file", "~/index.json", "JSON index file to load at startup and/or write to.")
    out = Option("cmdline", "index-out", "~/index.json", "Output file name for steno rule -> translation indices.")

    @pipe("start", "new_index")
    @pipe("index_load", "new_index")
    def load(self, filename:str="") -> Optional[Dict[str, dict]]:
        """ Load an index from disk if one is found. Ignore failures. """
        try:
            return self.engine_call("file_load", filename or self.file)
        except OSError:
            return None

    @pipe("index_save", "file_save")
    def save(self, d:Dict[str, dict], filename:str="") -> tuple:
        """ Save an index structure directly into JSON.
            Saving should not fail silently, unlike loading. If no save filename is given, use the default. """
        return (filename or self.out), d
