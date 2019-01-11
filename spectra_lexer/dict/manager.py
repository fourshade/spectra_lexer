from functools import partialmethod
from typing import List, Sequence

from spectra_lexer import Component, on, fork, pipe
from spectra_lexer.utils import merge


class ResourceManager(Component):

    files: Sequence[str] = ()  # Input filenames overridden by subclass default parameters or the command line.

    def __init_subclass__(cls) -> None:
        """ Create command decorators for each subclass based on its role/resource type. """
        s = cls._SUBTYPE()
        cls.start = on("start")(partialmethod(cls.start))
        cls.load = fork("dict_load_"+s, "new_"+s)(partialmethod(cls.load))
        cls.save = pipe("dict_save_"+s, "file_save", unpack=True)(partialmethod(cls.save))
        super().__init_subclass__()

    @classmethod
    def _SUBTYPE(cls) -> str:
        """ The last part of the role name is both the command suffix and the command line file option. """
        return cls.ROLE.rsplit("_", 1)[-1]

    def start(self, **opts) -> None:
        """ Save this component's command line input (if any) over any default. """
        file = opts.get(self._SUBTYPE())
        if file:
            self.files = [file]

    def load(self, filenames:Sequence[str]=()) -> object:
        """ Load and merge resources from disk. If no filenames are given by the command,
             load the one from defaults or the command line. """
        dicts = self._load(filenames or self.files)
        return self.parse(merge(dicts))

    def _load(self, filenames:Sequence[str]) -> List[dict]:
        """ Decode all files from the argument. If there's no files, just return that empty sequence. """
        return filenames and self.engine_call("file_load", *filenames)

    def parse(self, d:dict) -> object:
        """ Optional parse function to convert from raw disk format. May simply return the argument unchanged. """
        return d

    def save(self, filename:str, obj:object) -> tuple:
        """ Parse an object into raw form using reference data from the parser, then save it.
            If no save filename is given, use the first/only default file (if there's none, an IndexError is fine.) """
        return (filename or self.files[0]), self.inv_parse(obj)

    def inv_parse(self, obj:object) -> object:
        """ Optional parse function to convert to raw disk format. May simply return the argument unchanged. """
        return obj
