from typing import Dict

from spectra_lexer.core import COREApp, Component, Resource, Signal
from spectra_lexer.system import CmdlineOption, ConsoleCommand, SYSFile
from spectra_lexer.types.codec import JSONDict


class StenoIndex(JSONDict):
    pass


class LXIndex:

    @ConsoleCommand("index_load")
    def load(self, filename:str="") -> Dict[str, dict]:
        raise NotImplementedError

    @ConsoleCommand("index_save")
    def save(self, d:Dict[str, dict], filename:str="") -> None:
        raise NotImplementedError

    class NotFound:
        @Signal
        def on_index_not_found(self) -> None:
            raise NotImplementedError

    class Dict:
        index: StenoIndex = Resource()


class IndexManager(Component, LXIndex,
                   COREApp.Start):
    """ Translation index handler for the Spectra program.
        The structure is a dict of rule names, each mapped to a string dict of steno translations.
        Simple as it is, the structure is large and requires a lot of CPU load to process. """

    file = CmdlineOption("index-file", default="~/index.json",
                         desc="JSON index file to load on startup and/or write to.")
    out = CmdlineOption("index-out", default="~/index.json",
                        desc="Output file name for steno rule -> translation indices.")

    def on_app_start(self) -> None:
        self.load()

    def load(self, filename:str="") -> StenoIndex:
        """ Load an index from disk if one is found. Ask the user to make one on failure. """
        try:
            data = self.engine_call(SYSFile.read, filename or self.file)
            index = StenoIndex.decode(data)
            self._update(index)
            return index
        except OSError:
            self.engine_call(self.NotFound)
            return StenoIndex()

    def save(self, index:StenoIndex, filename:str="") -> None:
        """ Save an index structure directly into JSON. Sort all rules and translations by key and set them active.
            Saving should not fail silently, unlike loading. If no save filename is given, use the default. """
        self.engine_call(SYSFile.write, filename or self.out, index.encode(sort_keys=True))
        self._update(index)

    def _update(self, index:StenoIndex) -> None:
        """ Update the active index on save or load. """
        self.engine_call(self.Dict, index)
