""" Module for raw I/O operations as well as parsing file and resource paths. """

import fnmatch
import glob
import os
import sys
from typing import Iterator, List

from pkg_resources import resource_string, resource_listdir


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


class UserFilePath(FilePath):
    """ An identifier for a file in the user's app data directory. """

    # Default path components are for Linux, since it has several possible platform identifiers.
    DEFAULT_PATH_COMPONENTS = (".local", "share", "{0}")
    # Path components specific to Windows and Mac OS.
    PLATFORM_PATH_COMPONENTS = {"win32": ("AppData", "Local", "{0}", "{0}"),
                                "darwin": ("Library", "Application Support", "{0}")}

    def __new__(cls, s:str, user_path:str="", **options):
        """ If the prefix is ~appname/, it is a file from the user's application-specific data directory.
            If the prefix is ~/, it is specifically a file from THIS application's user data directory. """
        app_prefix, filename = s.split("/", 1)
        path_components = cls.PLATFORM_PATH_COMPONENTS.get(sys.platform) or cls.DEFAULT_PATH_COMPONENTS
        path_fmt = os.path.join("~", *path_components, filename)
        path = path_fmt.format(app_prefix or user_path)
        return FilePath(os.path.expanduser(path))


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


class NullPath(AbstractPath):
    """ A dummy class that reads nothing and writes to a black hole. """

    read = bytes
    write = lambda data: None
    _search = list


# Path prefixes and corresponding classes, in order of testing (should be from longest to shortest).
PATH_TYPES_BY_PREFIX = [("NUL", NullPath),
                        (":/",  AssetPath),
                        ("~",   UserFilePath),
                        ("",    FilePath)]


class PathIO:

    _root_paths: dict  # Contains base paths to search for assets and user data files.

    def __init__(self, **root_paths):
        self._root_paths = root_paths

    def read(self, *patterns:str, ignore_missing:bool=False) -> Iterator[bytes]:
        """ Expand each filename pattern by converting it to a path and using its path-dependent search.
            Load binary data strings from each valid file. Missing files may be skipped instead of raising. """
        for f in patterns:
            for path in self.to_path(f).search():
                try:
                    yield path.read()
                except OSError:
                    if not ignore_missing:
                        raise

    def write(self, data:bytes, filename:str) -> None:
        """ Write a binary data string to a file. """
        path = self.to_path(filename)
        path.write(data)

    def to_path(self, s:str) -> AbstractPath:
        """ Determine the type of resource path from a string by its prefix.
            When a matching class is found, strip the prefix and create the appropriate path identifier. """
        if isinstance(s, AbstractPath):
            return s
        for prefix, tp in PATH_TYPES_BY_PREFIX:
            if s.startswith(prefix):
                return tp(s[len(prefix):], **self._root_paths)
