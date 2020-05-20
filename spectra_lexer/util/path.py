""" Module for parsing file and resource paths. """

import os
import sys

# Default user path components are for Linux, since it has several possible platform identifiers.
DEFAULT_USERPATH_COMPONENTS = (".local", "share", "{0}")
# User path components specific to Windows and Mac OS.
PLATFORM_USERPATH_COMPONENTS = {"win32": ("AppData", "Local", "{0}", "{0}"),
                                "darwin": ("Library", "Application Support", "{0}")}


def user_data_directory(app_name:str) -> str:
    """ Find a Python application's user data directory based on a platform-specific path expansion.
        app_name - Name of app for which to find data files in the user's home directory. """
    path_components = PLATFORM_USERPATH_COMPONENTS.get(sys.platform) or DEFAULT_USERPATH_COMPONENTS
    path_fmt = os.path.join("~", *path_components)
    path = path_fmt.format(app_name)
    return os.path.expanduser(path)


def module_directory(mod_name:str) -> str:
    """ Find (or import) a module, find its filesystem path, and return just the directory.
        mod_name - Full name of Python module or package. """
    module = sys.modules.get(mod_name) or __import__(mod_name)
    return os.path.dirname(module.__file__)


class PrefixPathConverter:
    """ Deciphers resource paths based on prefix characters (such as ~ for user home). """

    def __init__(self) -> None:
        self._path_table = []  # Ordered list of all matchable path prefixes paired with their base path strings.

    def add(self, prefix:str, base_path:str) -> None:
        """ Add a substitute for a special prefix on a path string.
            Maintain the list in order from longest to shortest prefix for proper comparison. """
        entry = (prefix, os.path.normpath(base_path))
        self._path_table.append(entry)
        self._path_table.sort(key=lambda x: -len(x[0]))

    def expand(self, path:str) -> str:
        """ Check a path for special prefixes. If one is found, strip it and add its matching base path. """
        for prefix, base_path in self._path_table:
            if path.startswith(prefix):
                rel_path = path[len(prefix):]
                return os.path.join(base_path, rel_path)
        return path

    def convert(self, head:str, *tail:str, make_dirs=False) -> str:
        """ Convert a series of path segments into a full file path usable by open().
            If <make_dirs> is true, create directories as needed to make a valid path for write mode. """
        path = self.expand(head)
        if tail:
            path = os.path.join(path, *tail)
        if make_dirs:
            directory = os.path.dirname(path) or "."
            os.makedirs(directory, exist_ok=True)
        return path
