""" Module for reading Plover's user configuration. """

from configparser import ConfigParser
import json
import os
from typing import Iterator


class PloverConfig:
    """ Returns information about the user's Plover configuration. """

    DEFAULT_FILENAME = "plover.cfg"

    def __init__(self, base_path=".") -> None:
        self._base_path = base_path    # Base for relative file paths.
        self._parser = ConfigParser()

    def read(self, filename:str=None) -> None:
        """ Parse a Plover config file. """
        cfg_path = os.path.join(self._base_path, filename or self.DEFAULT_FILENAME)
        self._parser.read(cfg_path, encoding='utf-8')

    def dictionary_paths(self) -> Iterator[str]:
        """ Yield a full file path for each Plover dictionary listed in the config file. """
        # The config value we need is read as a string, but it must be decoded as a JSON array of objects.
        value = self._parser['System: English Stenotype']['dictionaries']
        dictionary_specs = json.loads(value)
        # Earlier keys override later ones in Plover, but dict.update does the opposite. Reverse the priority order.
        for spec in reversed(dictionary_specs):
            path = spec['path']
            # The paths start out relative to the location of the config file. Make them absolute.
            yield os.path.join(self._base_path, path)


def find_dictionaries(user_dir:str, cfg_filename:str=None, *, ext=None, ignore_errors=False) -> Iterator[str]:
    """ Load a Plover config file from a user data directory and yield file paths for the dictionaries.
        If <ext> is not None, only yield paths with that file extension.
        If <ignore_errors> is True, file and parsing errors will be silently ignored. """
    try:
        config = PloverConfig(user_dir)
        config.read(cfg_filename)
        for path in config.dictionary_paths():
            if ext is None or path.endswith(ext):
                yield path
    except (IndexError, KeyError, OSError, ValueError):
        if not ignore_errors:
            raise
