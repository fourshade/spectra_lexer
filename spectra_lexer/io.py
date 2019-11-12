""" Module for raw I/O operations as well as parsing file and resource paths. """

from configparser import ConfigParser
import glob
import json
import os
import sys
from typing import Dict, IO, List, TextIO, Union


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
    """ Performs filesystem I/O and transcoding for common formats. """

    _JSON_OBJ = Union[None, bool, int, float, str, tuple, list, dict]  # Python types supported by json module.

    def __init__(self, converter:BasePathConverter=None, *, encoding='utf-8') -> None:
        self._converter = converter or PrefixPathConverter()  # Converts relative or special file paths for open()ing.
        self._encoding = encoding                             # Encoding for all text-based files.

    def open(self, filename:str, mode='r', *args) -> Union[IO, TextIO]:
        """ Get a converted path corresponding to the <filename> and open it. Return the I/O stream.
            If writing or appending, create directories to the path as needed. """
        path = self._converter.convert(filename)
        if 'w' in mode or 'a' in mode:
            directory = os.path.dirname(path) or "."
            os.makedirs(directory, exist_ok=True)
        return open(path, mode, *args, encoding=self._encoding)

    def expand(self, pattern:str) -> List[str]:
        """ Return a list of valid filenames that resolve to a glob <pattern> after path conversion. """
        path = self._converter.convert(pattern)
        return glob.glob(path)

    def json_read(self, filename:str, *, comment_prefix:str=None) -> _JSON_OBJ:
        """ JSON standard library functions are among the fastest ways to load structured data in Python.
            Lines beginning with <comment_prefix> may be optionally located and removed before decoding. """
        with self.open(filename, 'r') as fp:
            data = fp.read()
        if comment_prefix is not None:
            # JSON doesn't care about leading or trailing whitespace anyway, so strip every line.
            stripped_line_iter = map(str.strip, data.splitlines())
            # Remove empty lines and comments before rejoining.
            stripped_lines = [line for line in stripped_line_iter if line and not line.startswith(comment_prefix)]
            data = "\n".join(stripped_lines)
        return json.loads(data)

    def json_write(self, obj:_JSON_OBJ, filename:str) -> None:
        """ Write an object to a JSON file. Dict key sorting helps some parsing and search algorithms run faster.
            An explicit flag is required to preserve Unicode symbols. """
        data = json.dumps(obj, sort_keys=True, ensure_ascii=False)
        with self.open(filename, 'w') as fp:
            fp.write(data)

    def cfg_read(self, filename:str, *, ignore_default=True) -> Dict[str, dict]:
        """ Read config settings from disk into a two-level nested dict. """
        parser = ConfigParser()
        with self.open(filename, 'r') as fp:
            parser.read_file(fp)
        sections = iter(parser)
        # The first section is the default section; ignore it unless specified otherwise.
        if ignore_default:
            next(sections)
        # Convert proxies from all other sections into dicts.
        return {sect: dict(parser[sect]) for sect in sections}

    def cfg_write(self, cfg:Dict[str, dict], filename:str) -> None:
        """ Write a two-level nested config dict into .cfg format. """
        parser = ConfigParser()
        parser.read_dict(cfg)
        with self.open(filename, 'w') as fp:
            parser.write(fp)
