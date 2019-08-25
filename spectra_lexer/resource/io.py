""" Module for raw I/O operations as well as parsing file and resource paths. """

from configparser import ConfigParser
import glob
import json
import os
import sys
from typing import IO, Iterator, List


class FilePath:
    """ A file identifier, created from an ordinary file path. """

    _path: str = ""  # Ordinary filesystem path string.

    def __init__(self, path:str) -> None:
        self._path = path

    def open(self, mode:str='r', *args) -> IO:
        """ Open the file from its path. If writing or appending, create directories to the path as needed. """
        if 'w' in mode or 'a' in mode:
            directory = os.path.dirname(self._path) or "."
            os.makedirs(directory, exist_ok=True)
        return open(self._path, mode, *args)

    def search(self) -> List[str]:
        """ Return a list containing path strings matching the identifier from the filesystem. """
        return glob.glob(self._path)


class AssetPath(FilePath):
    """ A built-in asset identifier from a Python package in the filesystem. """

    def __init__(self, filename:str, asset_package:str) -> None:
        module = sys.modules.get(asset_package) or __import__(asset_package)
        module_path = os.path.dirname(module.__file__)
        full_path = os.path.join(module_path, *filename.split('/'))
        super().__init__(full_path)


class UserFilePath(FilePath):
    """ A file identifier for application data from the current user's home directory. """

    # Default user path components are for Linux, since it has several possible platform identifiers.
    DEFAULT_USERPATH_COMPONENTS = (".local", "share", "{0}")
    # User path components specific to Windows and Mac OS.
    PLATFORM_USERPATH_COMPONENTS = {"win32": ("AppData", "Local", "{0}", "{0}"),
                                    "darwin": ("Library", "Application Support", "{0}")}

    def __init__(self, filename:str, user_path:str) -> None:
        """ Find the application's user data directory based on the platform and expand the path. """
        path_components = self.PLATFORM_USERPATH_COMPONENTS.get(sys.platform) or self.DEFAULT_USERPATH_COMPONENTS
        path_fmt = os.path.join("~", *path_components, filename)
        path = path_fmt.format(user_path)
        full_path = os.path.expanduser(path)
        super().__init__(full_path)


class PloverConfigPath(UserFilePath):
    """ A specific identifier for the config file in the user's Plover installation with dictionary paths. """

    def __init__(self, filename:str) -> None:
        super().__init__(filename, "plover")

    def search(self) -> List[str]:
        """ Attempt to load a Plover config file and return all dictionary files in reverse priority order
            (required since earlier keys override later ones in Plover, but dict.update does the opposite). """
        try:
            cfg = ConfigParser()
            cfg.read(self._path)
            if cfg:
                # Dictionaries are located in the same directory as the config file.
                # The section we need is read as a string, but it must be decoded as a JSON array.
                section = cfg['System: English Stenotype']['dictionaries']
                dict_files = json.loads(section)[::-1]
                plover_dir = os.path.split(self._path)[0]
                return [os.path.join(plover_dir, e['path']) for e in dict_files]
        except (KeyError, OSError, ValueError):
            # Catch-all for file loading errors. Just assume the required files aren't there and move on.
            pass
        return []


class PathConverter:
    """ Transforms filename path strings into path objects based on prefixes. """

    _asset_package: str  # Full name of Python package to search for application assets.
    _user_path: str      # Base path to search for app data files within the user's home directory.

    def __init__(self, asset_package:str="", user_path:str="") -> None:
        self._asset_package = asset_package
        self._user_path = user_path

    def __call__(self, filename:str) -> FilePath:
        """ Determine the type of path from a filename string by its prefix, testing from longest to shortest.
            When a matching class is found, strip the prefix and create the appropriate path identifier. """
        if filename.startswith("~PLOVER/"):
            return PloverConfigPath(filename[8:])
        if filename.startswith(":/"):
            return AssetPath(filename[2:], self._asset_package)
        if filename.startswith("~/"):
            return UserFilePath(filename[2:], self._user_path)
        return FilePath(filename)


class PathIO:
    """ Opens, reads, and writes filename paths that may point to special places. """

    def __init__(self, *args) -> None:
        self._convert = PathConverter(*args)

    def open(self, filename:str, *args) -> IO:
        """ Get a path object corresponding to the specified file and open it. Return the I/O stream. """
        path = self._convert(filename)
        return path.open(*args)

    def read(self, filename:str) -> bytes:
        """ Open and read an entire file as a binary data string. """
        with self.open(filename, 'rb') as fp:
            return fp.read()

    def read_all(self, *patterns:str, ignore_missing:bool=False) -> Iterator[bytes]:
        """ Expand each filename pattern by converting it to a path and using its path-dependent search.
            Load binary data strings from each valid file. Missing files may be skipped instead of raising. """
        for f in patterns:
            for filename in self._convert(f).search():
                try:
                    yield self.read(filename)
                except OSError:
                    if not ignore_missing:
                        raise

    def write(self, data:bytes, filename:str) -> None:
        """ Write a binary data string to a file. """
        with self.open(filename, 'wb') as fp:
            fp.write(data)
