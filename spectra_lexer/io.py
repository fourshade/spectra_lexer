""" Module for raw I/O operations as well as parsing file and resource paths. """

import glob
from json import JSONDecoder
import os
import sys
from typing import Any, IO, Iterator, TextIO, Union


class BasePathConverter:
    """ Abstract base class for deciphering file paths that may point to special places. """

    def convert(self, filename:str) -> str:
        """ Convert a resource <filename> into a filesystem path which is directly usable by open(). """
        raise NotImplementedError


class AssetPathConverter(BasePathConverter):
    """ Deciphers file paths that point to built-in application assets. """

    def __init__(self, root_package:str) -> None:
        self._root_package = root_package  # Full name of Python package to search for application assets.

    def convert(self, filename:str) -> str:
        """ Find (or import) the required module, then find its filesystem path and combine it with the filename. """
        module = sys.modules.get(self._root_package) or __import__(self._root_package)
        module_path = os.path.dirname(module.__file__)
        return os.path.join(module_path, *filename.split('/'))


class UserPathConverter(BasePathConverter):
    """ Deciphers file paths that point to the user data directory for a specific app. """

    # Default user path components are for Linux, since it has several possible platform identifiers.
    DEFAULT_USERPATH_COMPONENTS = (".local", "share", "{0}")
    # User path components specific to Windows and Mac OS.
    PLATFORM_USERPATH_COMPONENTS = {"win32": ("AppData", "Local", "{0}", "{0}"),
                                    "darwin": ("Library", "Application Support", "{0}")}

    def __init__(self, app_name:str) -> None:
        self._app_name = app_name   # Name of app for which to find data files in the user's home directory.

    def convert(self, filename:str) -> str:
        """ Find the application's user data directory based on the platform and expand the path. """
        path_components = self.PLATFORM_USERPATH_COMPONENTS.get(sys.platform) or self.DEFAULT_USERPATH_COMPONENTS
        path_fmt = os.path.join("~", *path_components, filename)
        path = path_fmt.format(self._app_name)
        return os.path.expanduser(path)


class PrefixPathConverter(BasePathConverter):
    """ Deciphers resource paths using other converters based on prefix characters (such as ~ for user home). """

    def __init__(self) -> None:
        self._converters = {}  # Mapping of valid prefixes to their converter objects.
        self._prefixes = []    # Ordered list of all matchable path prefixes.

    def add(self, prefix:str, converter:BasePathConverter) -> None:
        """ Add a converter corresponding to a special prefix on a path string.
            Maintain the prefix list in order from longest to shortest for proper comparison. """
        self._converters[prefix] = converter
        self._prefixes = sorted(self._converters, key=len, reverse=True)

    def convert(self, filename:str) -> str:
        """ Test a <filename> string for special path prefixes. Return it unchanged if nothing matches.
            If a matching prefix is found, strip it and use its converter on the remaining characters. """
        for prefix in filter(filename.startswith, self._prefixes):
            raw_path = filename[len(prefix):]
            return self._converters[prefix].convert(raw_path)
        return filename


class ResourceIO:
    """ Performs filesystem I/O using specially formatted file paths. """

    _IOSTREAM = Union[IO, TextIO]

    def __init__(self, converter:BasePathConverter=None, *, encoding='utf-8') -> None:
        self._converter = converter or PrefixPathConverter()  # Converts relative or special file paths for open()ing.
        self._encoding = encoding                             # Encoding for all text-based files.

    def open(self, filename:str, *args) -> _IOSTREAM:
        """ Get a converted path corresponding to the <filename> and open it. Return the I/O stream. """
        path = self._converter.convert(filename)
        return self._open(path, *args)

    def open_all(self, pattern:str, *args) -> Iterator[_IOSTREAM]:
        """ Open all valid files that resolve to a glob <pattern> after path conversion and yield each I/O stream. """
        path = self._converter.convert(pattern)
        for p in glob.glob(path):
            yield self._open(p, *args)

    def _open(self, path:str, mode='r', *args) -> _IOSTREAM:
        """ Open the file at <path> using <mode> and return the I/O stream.
            If writing or appending, create directories to the path as needed. """
        if 'w' in mode or 'a' in mode:
            directory = os.path.dirname(path) or "."
            os.makedirs(directory, exist_ok=True)
        return open(path, mode, *args, encoding=self._encoding)


class CSONLoader:
    """ Reads from non-standard JSON files with full-line comments (CSON = commented JSON). """

    def __init__(self, comment_prefix="#", **kwargs) -> None:
        self._comment_prefix = comment_prefix  # Starting character(s) for comments in CSON files.
        self._decoder = JSONDecoder(**kwargs)

    def load(self, fp:TextIO) -> Any:
        """ Read an object from a non-standard JSON file with full-line comments.
            JSON doesn't care about leading or trailing whitespace anyway, so strip every line first. """
        stripped_line_iter = map(str.strip, fp)
        data_lines = [line for line in stripped_line_iter
                      if line and not line.startswith(self._comment_prefix)]
        data = "\n".join(data_lines)
        return self._decoder.decode(data)
