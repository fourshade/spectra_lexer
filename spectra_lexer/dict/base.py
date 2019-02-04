from functools import partialmethod
from typing import List, Sequence

from spectra_lexer import Component, fork, pipe
from spectra_lexer.utils import merge


class ResourceManager(Component):
    """ Handles conversion and parsing required for file operations on specific resource types. """

    ROLE = "dict"

    files: Sequence[str] = ()  # Input filenames overridden by subclass default parameters or the command line.

    def __init_subclass__(cls) -> None:
        """ Create command decorators for each subclass based on its role/resource type. """
        s = cls._SUBTYPE()
        cls.start = pipe("start", "dict_load_"+s, unpack=True)(partialmethod(cls.start))
        cls.load = fork("dict_load_"+s, "new_"+s)(partialmethod(cls.load))
        cls.save = pipe("dict_save_"+s, "file_save", unpack=True)(partialmethod(cls.save))
        super().__init_subclass__()

    @classmethod
    def _SUBTYPE(cls) -> str:
        """ The last part of the role name is both the command suffix and the command line file option. """
        return cls.ROLE.rsplit("_", 1)[-1]

    def start(self, **opts) -> object:
        """ If there is a command line option for this component, even if empty, attempt to load its resource.
            If the option is not empty (or otherwise evaluates True), also save it over the default first. """
        file = opts.get(self._SUBTYPE())
        if file is not None:
            if file:
                self.files = [file]
            return ()

    def load(self, filenames:Sequence[str]=()) -> dict:
        """ Load and merge resources from disk. If no filenames are given by the command,
            load the one from defaults or the command line. """
        dicts = self._load(filenames or self.files)
        return self.parse(merge(dicts))

    def _load(self, filenames:Sequence[str]) -> List[dict]:
        """ Decode all files from the argument. If there's no files, just return that empty sequence. """
        return filenames and self.engine_call("file_load", *filenames)

    def parse(self, d:dict) -> dict:
        """ Optional parse function to convert from raw disk format. May simply return the argument unchanged. """
        return d

    def save(self, filename:str, obj:object) -> tuple:
        """ Parse an object into raw form using reference data from the parser, then save it.
            If no save filename is given, use the first/only default file (if there's none, an IndexError is fine.) """
        return (filename or self.files[0]), self.inv_parse(obj)

    def inv_parse(self, obj:object) -> object:
        """ Optional parse function to convert to raw disk format. May simply return the argument unchanged. """
        return obj
