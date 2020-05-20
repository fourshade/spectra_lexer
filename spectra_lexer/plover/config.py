""" Module for reading Plover's user configuration. """

from configparser import ConfigParser
import json
import os
from typing import List


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

    def dictionary_paths(self) -> List[str]:
        """ Return a list of full file paths for the Plover dictionaries listed in the config file. """
        # The config value we need is read as a string, but it must be decoded as a JSON array of objects.
        value = self._parser['System: English Stenotype']['dictionaries']
        dictionary_specs = json.loads(value)
        # Earlier keys override later ones in Plover, but dict.update does the opposite. Reverse the priority order.
        dictionary_specs.reverse()
        # The paths start out relative to the location of the config file. Make them absolute.
        return [os.path.join(self._base_path, spec['path']) for spec in dictionary_specs]


def find_dictionaries(user_dir:str, cfg_filename:str=None, *, ignore_errors=False) -> List[str]:
    """ Load a Plover config file from a user data directory and return the full file paths for the dictionaries.
        Return an empty list on a file or parsing error if <ignore_errors> is True. """
    try:
        config = PloverConfig(user_dir)
        config.read(cfg_filename)
        return config.dictionary_paths()
    except (IndexError, KeyError, OSError, ValueError):
        if not ignore_errors:
            raise
        return []
