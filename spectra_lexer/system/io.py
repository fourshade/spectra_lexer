""" Module for raw I/O operations as well as parsing file and resource paths. """

import fnmatch
import glob
import os
import sys
from typing import Iterator, List

from pkg_resources import resource_string, resource_listdir


class AbstractPath:
    """ Abstract class for a resource path identifier. """

    _path: str = ""

    def read(self) -> bytes:
        """ Open and read a file into a byte string. """
        raise TypeError("Reading of this resource type is not supported.")

    def write(self, contents:bytes) -> None:
        """ Open a new file and write a byte string. """
        raise TypeError("Writing of this resource type is not supported.")

    def search(self) -> list:
        """ Return a list containing paths matching the identifier. """
        raise TypeError("Searching of this resource type is not supported.")

    def __str__(self) -> str:
        """ Return the ordinary file path string associated with this object. """
        return self._path


class FilePath(AbstractPath):
    """ A file identifier, created from an ordinary file path. """

    def __init__(self, s:str):
        """ Make a new path with the path string. """
        self._path = s

    def read(self) -> bytes:
        """ Open and read an entire text file as a byte string. """
        with open(self._path, 'rb') as fp:
            return fp.read()

    def write(self, contents:bytes) -> None:
        """ Write the given byte string as the sole contents of a file.
            If the directory path doesn't exist, create it. """
        directory = os.path.dirname(self._path) or "."
        os.makedirs(directory, exist_ok=True)
        with open(self._path, 'wb') as fp:
            fp.write(contents)

    def search(self) -> List[AbstractPath]:
        """ Return a list containing paths matching the identifier from the filesystem. """
        return [*map(FilePath, glob.glob(self._path))]


class UserFilePath(FilePath):

    # Default user path components are for Linux, since it has several possible platform identifiers.
    DEFAULT_USERPATH_COMPONENTS = (".local", "share", "{0}")
    # User path components specific to Windows and Mac OS.
    PLATFORM_USERPATH_COMPONENTS = {"win32": ("AppData", "Local", "{0}", "{0}"),
                                    "darwin": ("Library", "Application Support", "{0}")}

    def __init__(self, s:str, user_path:str=""):
        """ If the prefix is ~appname/, it is a file from the user's application-specific data directory.
            If the prefix is ~/, it is specifically a file from THIS application's user data directory. """
        app_prefix, filename = s.split("/", 1)
        path_components = self.PLATFORM_USERPATH_COMPONENTS.get(sys.platform) or self.DEFAULT_USERPATH_COMPONENTS
        path_fmt = os.path.join("~", *path_components, filename)
        path = path_fmt.format(app_prefix or user_path)
        full_path = os.path.expanduser(path)
        super().__init__(full_path)


class AssetPath(AbstractPath):
    """ A built-in asset identifier, created by using pkg_resources. """

    _root: str  # Start directory for all assets.

    def __init__(self, s:str, asset_path:str=""):
        """ Make a new path with the path string and root path. """
        self._path = s
        self._root = asset_path

    def read(self) -> bytes:
        """ Return a byte string representation of a built-in asset. """
        return resource_string(self._root, self._path)

    def search(self) -> List[AbstractPath]:
        """ Return a list containing resource paths matching the identifier from a built-in asset directory. """
        pathname, pattern = os.path.split(self._path)
        dir_list = resource_listdir(self._root, pathname)
        asset_names = fnmatch.filter(dir_list, pattern)
        return [AssetPath(os.path.join(pathname, n), self._root) for n in asset_names]


class NullPath(AbstractPath):
    """ A dummy class that reads nothing and writes to a black hole. """

    _path = "NULL"
    read = bytes
    write = lambda *args: None
    search = list


class PathIO:

    _asset_path: str  # Base path to search for application assets.
    _user_path: str   # Base path to search for user data files.

    def __init__(self, asset_path:str="", user_path:str=""):
        self._asset_path = asset_path
        self._user_path = user_path

    def read(self, *patterns:str, ignore_missing:bool=False) -> Iterator[bytes]:
        """ Expand each filename pattern by converting it to a path and using its path-dependent search.
            Load binary data strings from each valid file. Missing files may be skipped instead of raising. """
        for f in patterns:
            for path in self._to_path(f).search():
                try:
                    yield path.read()
                except OSError:
                    if not ignore_missing:
                        raise

    def write(self, data:bytes, filename:str) -> None:
        """ Write a binary data string to a file. """
        path = self._to_path(filename)
        path.write(data)

    def expand(self, filename:str) -> str:
        """ Expand a filename pattern by converting it to a path and back. """
        return str(self._to_path(filename))

    def exists(self, filename:str) -> bool:
        """ Return True if <filename> refers to at least one existing file after path conversion. """
        return bool(self._to_path(filename).search())

    def _to_path(self, s) -> AbstractPath:
        """ Determine the type of resource path from a string by its prefix, testing from longest to shortest.
            When a matching class is found, strip the prefix and create the appropriate path identifier. """
        if s == "NUL":
            return NullPath()
        if s.startswith(":/"):
            return AssetPath(s[2:], self._asset_path)
        if s.startswith("~"):
            return UserFilePath(s[1:], self._user_path)
        return FilePath(s)
