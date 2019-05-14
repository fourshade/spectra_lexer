""" Module for raw I/O operations as well as parsing file and resource paths. """

import fnmatch
import glob
import os
from typing import Iterable, List

from appdirs import user_data_dir
from pkg_resources import resource_listdir, resource_string

from .app import SYSApp
from spectra_lexer.core import Command, Component
from spectra_lexer.types import prefix_index

# Records resource types to check for membership by prefix.
TYPES_BY_PREFIX = use_if_path_startswith = prefix_index()


class AbstractPath(str):
    """ Abstract class for a resource path identifier. """

    _root: str  # Start directory for this path type.

    def __new__(cls, s:str, root:str="", **options):
        """ Make a new path with the path string. Subclasses may use the options. """
        self = super().__new__(cls, s)
        self._root = root
        return self

    def read(self) -> bytes:
        """ Open and read a file into a byte string. """
        raise TypeError("Reading of this resource type is not supported.")

    def write(self, contents:bytes) -> None:
        """ Open a new file and write a byte string. """
        raise TypeError("Writing of this resource type is not supported.")

    def search(self) -> list:
        """ Return a list containing resources matching the identifier from the filesystem. """
        return [self.__class__(s, self._root) for s in self._search()]

    def _search(self) -> List[str]:
        raise TypeError("Searching of this resource type is not supported.")


class SYSFile:

    @Command
    def read(self, file_path:str, *, ignore_missing:bool=False) -> bytes:
        """ Attempt to load a resource given by file path. Missing files may return b"" instead of raising. """
        raise NotImplementedError

    @Command
    def read_all(self, file_paths:Iterable[str], *, ignore_missing:bool=False) -> List[bytes]:
        """ Attempt to load all resources in the given file paths. Missing files may be ignored instead of raising. """
        raise NotImplementedError

    @Command
    def write(self, file_path:str, data:bytes) -> None:
        """ Attempt to save byte data to a file given by path. """
        raise NotImplementedError


class FileHandler(Component, SYSFile,
                  SYSApp.AssetPath, SYSApp.UserPath):

    def read(self, file_path:str, *, ignore_missing:bool=False) -> bytes:
        try:
            return self._to_path(file_path).read()
        except OSError:
            if not ignore_missing:
                raise
            return b""

    def read_all(self, file_paths:Iterable[str], **kwargs) -> List[bytes]:
        """ Try to expand each path as a wildcard pattern before reading. """
        expanded = [path for f in file_paths for path in self._to_path(f).search()]
        return [*filter(None, [self.read(path, **kwargs) for path in expanded])]

    def _to_path(self, s:str) -> AbstractPath:
        """ Determine the type of resource from a string by its prefix and create the appropriate path identifier. """
        if isinstance(s, AbstractPath):
            return s
        stripped, cls = TYPES_BY_PREFIX[s]
        return cls(stripped, asset_path=self.asset_path, user_path=self.user_path)

    def write(self, file_path:str, data:bytes) -> None:
        self._to_path(file_path).write(data)


@use_if_path_startswith.default()
class FilePath(AbstractPath):
    """ A file identifier, created from an ordinary file path. Will be used if nothing else matches. """

    def read(self) -> bytes:
        """ Open and read an entire text file as a byte string. """
        with open(self, 'rb') as fp:
            return fp.read()

    def write(self, contents:bytes) -> None:
        """ Write the given byte string as the sole contents of a file.
            If the directory path doesn't exist, create it. """
        directory = os.path.dirname(self) or "."
        os.makedirs(directory, exist_ok=True)
        with open(self, 'wb') as fp:
            fp.write(contents)

    def _search(self) -> List[str]:
        """ Return a list containing resources matching the identifier from the filesystem. """
        return glob.glob(self)


@use_if_path_startswith("~")
class UserFilePath(FilePath):
    """ An identifier for a file in the user's app data directory. """

    def __new__(cls, s:str, user_path:str="", **options):
        """ If the prefix is ~appname/, it is a file from the user's application-specific data directory.
            If the prefix is ~/, it is specifically a file from THIS application's user data directory. """
        app_prefix, filename = s.split("/", 1)
        directory = user_data_dir(app_prefix or user_path)
        return FilePath(os.path.join(directory, filename))


@use_if_path_startswith(":/")
class AssetPath(AbstractPath):
    """ A built-in asset identifier, created by using pkg_resources. """

    def __new__(cls, s:str, asset_path:str="", **options):
        """ Make a new path with the path string and options. """
        return super().__new__(cls, s, asset_path)

    def read(self) -> bytes:
        """ Return a byte string representation of a built-in asset. """
        return resource_string(self._root, self)

    def _search(self) -> List[str]:
        """ Return a list containing resources matching the identifier from a built-in asset directory. """
        pathname, pattern = os.path.split(self)
        dir_list = resource_listdir(self._root, pathname)
        asset_names = fnmatch.filter(dir_list, pattern)
        return [os.path.join(pathname, n) for n in asset_names]


@use_if_path_startswith("NUL")
class NullPath(AbstractPath):
    """ A dummy class that reads nothing and writes to a black hole. """

    read = lambda self: b""
    write = lambda *args: None
    _search = lambda self: [self]
