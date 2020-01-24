""" Module for parsing file and resource paths. """

import os
import sys


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

    def convert(self, path:str, *, make_dirs=False) -> str:
        """ Convert a specially formatted <path> string into a full file path usable by open().
            If a special prefix is found, strip it and use its converter on the remaining characters.
            If <make_dirs> is true, create directories as needed to make a valid path for write mode. """
        for prefix in self._prefixes:
            if path.startswith(prefix):
                converter = self._converters[prefix]
                raw_path = path[len(prefix):]
                path = converter.convert(raw_path)
                break
        if make_dirs:
            directory = os.path.dirname(path) or "."
            os.makedirs(directory, exist_ok=True)
        return path
