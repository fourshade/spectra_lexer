from typing import Iterable, Iterator, Type

from .path import AbstractPath
from ..base import SYS
from spectra_lexer.types.codec import AbstractCodec


class FileHandler(SYS):

    def SYSFileLoad(self, codec_cls:Type[AbstractCodec], *patterns:str, ignore_missing:bool=False, **kwargs):
        bytes_iter = self._read_data(patterns, ignore_missing)
        return codec_cls.decode(*bytes_iter, **kwargs)

    def _read_data(self, patterns:Iterable[str], ignore_missing:bool) -> Iterator[bytes]:
        """ Attempt to load binary data strings from files. Missing files may be skipped instead of raising. """
        for path in self._expand(patterns):
            try:
                yield path.read()
            except OSError:
                if not ignore_missing:
                    raise

    def _expand(self, patterns:Iterable[str]) -> Iterator[AbstractPath]:
        """ Try to expand wildcards in each filename pattern before reading. """
        for f in patterns:
            path = self._to_path(f)
            yield from path.search()

    def _to_path(self, s:str) -> AbstractPath:
        return AbstractPath.from_string(s, **self.root_paths())

    def SYSFileSave(self, obj:AbstractCodec, filename:str, **kwargs) -> None:
        path = self._to_path(filename)
        data = obj.encode(**kwargs)
        path.write(data)

    @classmethod
    def root_paths(cls) -> dict:
        """ The name of this class's root package is used as a default path for built-in assets and user files. """
        root_path = cls.__module__.split(".", 1)[0]
        return {"asset_path": root_path,  # Root directory for application assets.
                "user_path":  root_path}  # Root directory for user data files.
