""" Module for raw I/O operations as well as parsing file and resource paths. """

from configparser import ConfigParser
import glob
import json
import os
import sys
from typing import Callable, Dict, IO, List, TextIO, Union


class FilePath:
    """ A file identifier, created from an ordinary file path. """

    def __init__(self, path:str) -> None:
        self._path = path  # Ordinary filesystem path string.

    def open(self, mode:str='r', *args) -> IO:
        """ Open the file from its path. If writing or appending, create directories to the path as needed. """
        if 'w' in mode or 'a' in mode:
            directory = os.path.dirname(self._path) or "."
            os.makedirs(directory, exist_ok=True)
        return open(self._path, mode, *args)

    def read(self) -> bytes:
        """ Open and read the entire file as a binary data string. """
        with self.open('rb') as fp:
            return fp.read()

    def write(self, data:bytes) -> None:
        """ Write a binary data string to the file. """
        with self.open('wb') as fp:
            fp.write(data)

    def expand(self) -> List[str]:
        """ Return a list containing path strings matching the identifier from the filesystem. """
        return glob.glob(self._path)


class PathIO:
    """ Opens, reads, and writes filename paths that may need conversion first. """

    # The name of this module's root package is used as a default path for built-in assets and user files.
    ROOT_PACKAGE = __package__.split(".", 1)[0]
    # Default user path components are for Linux, since it has several possible platform identifiers.
    DEFAULT_USERPATH_COMPONENTS = (".local", "share", "{0}")
    # User path components specific to Windows and Mac OS.
    PLATFORM_USERPATH_COMPONENTS = {"win32": ("AppData", "Local", "{0}", "{0}"),
                                    "darwin": ("Library", "Application Support", "{0}")}

    def __init__(self, asset_package:str=ROOT_PACKAGE, user_path:str=ROOT_PACKAGE) -> None:
        """ Deciphers file paths that may point to special places. """
        self._asset_package = asset_package  # Full name of Python package to search for application assets.
        self._user_path = user_path          # Base path to search for app data files within the user's home directory.

    def _convert(self, filename:str) -> FilePath:
        """ Determine the type of path from a filename string by its prefix, testing from longest to shortest.
            When a matching class is found, strip the prefix and create the appropriate path identifier. """
        if filename.startswith(":/"):
            # A built-in asset identifier from a Python package in the filesystem.
            filename = self._convert_asset_path(filename[2:])
        elif filename.startswith("~/"):
            # A file identifier for application data from the current user's home directory.
            filename = self._convert_user_path(filename[2:])
        return FilePath(filename)

    def _convert_asset_path(self, filename:str) -> str:
        """ Find (or import) the required module, then find its filesystem path and combine it with the filename. """
        module = sys.modules.get(self._asset_package) or __import__(self._asset_package)
        module_path = os.path.dirname(module.__file__)
        return os.path.join(module_path, *filename.split('/'))

    def _convert_user_path(self, filename:str) -> str:
        """ Find the application's user data directory based on the platform and expand the path. """
        path_components = self.PLATFORM_USERPATH_COMPONENTS.get(sys.platform) or self.DEFAULT_USERPATH_COMPONENTS
        path_fmt = os.path.join("~", *path_components, filename)
        path = path_fmt.format(self._user_path)
        return os.path.expanduser(path)

    def open(self, filename:str, *args) -> Union[IO, TextIO]:
        """ Get a path object corresponding to the specified file and open it. Return the I/O stream. """
        return self._convert(filename).open(*args)

    def read(self, filename:str) -> bytes:
        """ Open and read an entire file as a binary data string. """
        return self._convert(filename).read()

    def write(self, data:bytes, filename:str) -> None:
        """ Write a binary data string to a file. """
        self._convert(filename).write(data)

    def expand(self, pattern:str) -> List[str]:
        """ Expand a filename pattern by converting it to a path and using its path-dependent search. """
        return self._convert(pattern).expand()


class _ResourceIO(PathIO):
    """ Performs filesystem I/O and transcoding between several formats. """

    def __init__(self, *args, encoding='utf-8', comment_prefixes=b"#/", **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._encoding = encoding                       # Encoding for all text-based files.
        self._comment_prefixes = set(comment_prefixes)  # Allowed prefixes for comments in CSON files.

    def _read_merge(self, read_fn:Callable[[str], dict], *patterns:str, check_keys=False) -> dict:
        """ Read and merge dicts from files on disk. """
        raw_dict = {}
        for p in patterns:
            for d in map(read_fn, self.expand(p)):
                if check_keys and raw_dict:
                    # Check for key conflicts between this dict and previous ones before merging.
                    conflicts = d.keys() & raw_dict.keys()
                    if conflicts:
                        raise ValueError(f"Found keys appearing more than once: {conflicts}")
                raw_dict.update(d)
        return raw_dict

    def json_read(self, filename:str) -> dict:
        """ JSON standard library functions are among the fastest ways to load structured data in Python. """
        data = self.read(filename)
        return json.loads(data)

    def json_read_merge(self, *patterns:str, **kwargs) -> dict:
        """ Find all JSON dicts whose filename resolves to one of <patterns> and return them merged. """
        return self._read_merge(self.json_read, *patterns, **kwargs)

    def json_write(self, d:dict, filename:str) -> None:
        """ Write a dict to a JSON file. Key sorting helps some parsing and search algorithms run faster.
            An explicit flag is required to preserve Unicode symbols. """
        data = json.dumps(d, sort_keys=True, ensure_ascii=False).encode(self._encoding)
        self.write(data, filename)

    def cson_read(self, filename:str) -> dict:
        """ Read and decode a JSON file with full-line standalone comments (CSON = commented JSON). """
        data = self.read(filename)
        # JSON doesn't care about leading or trailing whitespace, so strip every line.
        stripped_line_iter = map(bytes.strip, data.splitlines())
        # Empty lines and lines starting with a comment tag after stripping are removed before parsing.
        data_lines = [line for line in stripped_line_iter if line and line[0] not in self._comment_prefixes]
        data = b"\n".join(data_lines)
        return json.loads(data)

    def cson_read_merge(self, *patterns:str, **kwargs) -> dict:
        """ Find all CSON dicts whose filename resolves to one of <patterns> and return them merged. """
        return self._read_merge(self.cson_read, *patterns, **kwargs)

    def cfg_read(self, filename:str) -> Dict[str, dict]:
        """ Read config settings from disk into a two-level nested dict. """
        parser = ConfigParser()
        with self.open(filename, 'r') as fp:
            parser.read_file(fp)
        sects = list(parser)
        # The first section is the default section; ignore it. Convert all other proxies into dicts.
        return {sect: dict(parser[sect]) for sect in sects[1:]}

    def cfg_write(self, cfg:Dict[str, dict], filename:str) -> None:
        """ Write a two-level nested config dict into .cfg format. """
        parser = ConfigParser()
        parser.read_dict(cfg)
        with self.open(filename, 'w') as fp:
            parser.write(fp)


class ResourceIO(_ResourceIO):
    """ Adds a specific identifier to search the user's Plover installation for dictionaries. """

    PLOVER_TRANSLATIONS = "$PLOVER_TRANSLATIONS"  # Sentinel pattern to load the user's Plover dictionaries.

    def expand(self, pattern:str) -> List[str]:
        """ If the sentinel is given, search the user's local app data for the Plover config file.
            Parse the dictionaries section and return all dictionary filenames in reverse priority order
            (required since earlier keys override later ones in Plover, but dict.update does the opposite). """
        if pattern == self.PLOVER_TRANSLATIONS:
            try:
                io = PathIO(user_path="plover")
                path = io.expand("~/plover.cfg")[0]
                cfg = self.cfg_read(path)
                # Dictionaries are located in the same directory as the config file.
                # The section we need is read as a string, but it must be decoded as a JSON array.
                section = cfg['System: English Stenotype']['dictionaries']
                dict_files = json.loads(section)[::-1]
                plover_dir = os.path.split(path)[0]
                return [os.path.join(plover_dir, e['path']) for e in dict_files]
            except (IndexError, KeyError, OSError, ValueError):
                # Catch-all for file and parsing errors. The correct files aren't available, so just move on.
                return []
        return super().expand(pattern)
