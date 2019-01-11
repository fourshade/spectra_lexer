from functools import partialmethod
from typing import Iterable, List

from spectra_lexer import Component, on, fork, pipe
from spectra_lexer.utils import merge


class ResourceManager(Component):

    CMD_SUFFIX: str  # String designator for a subclass's engine commands.
    OPT_KEY: str     # String designator for a subclass's command line option.

    filenames: list = None  # List of input filenames from the command line.

    def __init_subclass__(cls) -> None:
        """ Create command decorators for each subclass based on its resource type. """
        s = cls.CMD_SUFFIX
        cls.start = on("start")(partialmethod(cls.start))
        cls.load = fork("dict_load_"+s, "new_"+s)(partialmethod(cls.load))
        cls.save = pipe("dict_save_"+s, "file_save", unpack=True)(partialmethod(cls.save))
        super().__init_subclass__()

    def start(self, **opts):
        """ Save this component's command line input (if any). If it is just a string, save it as a one-item list. """
        file = self.filenames = opts.get(self.OPT_KEY)
        if isinstance(file, str):
            self.filenames = [file]

    def load(self, filenames:Iterable[str]=()) -> object:
        """ Load and merge resources from disk. If no filenames are given by the command, load the ones provided
            at the command line. If none were given there either, attempt a default fallback method. """
        if filenames:
            dicts = self._load(filenames)
        elif self.filenames:
            dicts = self._load(self.filenames)
        else:
            dicts = self.load_default()
        return self.parse(merge(dicts))

    def _load(self, filenames:Iterable[str]) -> List[dict]:
        return [self.engine_call("file_load", f) for f in filenames]

    def load_default(self) -> List[dict]:
        return []

    def parse(self, d:dict) -> object:
        return d

    def save(self, filename:str, obj:object) -> tuple:
        """ Parse an object into raw form using reference data from the parser, then save it. """
        return filename, self.inv_parse(obj)

    def inv_parse(self, obj:object) -> object:
        return obj
