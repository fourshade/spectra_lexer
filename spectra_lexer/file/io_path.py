""" Module for raw I/O operations as well as parsing file and resource paths. """

import configparser
import json
import os
from typing import List

from pkg_resources import resource_listdir, resource_string

from spectra_lexer.utils import abstract_method

# TODO: Put these into a config file somewhere.
# Package and resource paths containing assets such as the built-in JSON-based rules files.
_ASSETS_PACKAGE_PATH: str = __name__.split(".", 1)[0]
_ASSETS_RESOURCE_PATH: str = "assets"


class Readable(str):
    """ Marker class for a readable resource identifier. """
    read = abstract_method


class Writeable(str):
    """ Marker class for a writable resource identifier. """
    write = abstract_method


class File(Readable, Writeable):
    """ A file identifier, created from an ordinary file path. """
    def read(self) -> str:
        """ Open and read an entire text file as a UTF-8 encoded string. """
        with open(self, 'rb') as fp:
            contents = fp.read().decode('utf-8')
        return contents

    def write(self, contents:str) -> None:
        """ Write the given string as the sole contents of a UTF-8 text file  """
        with open(self, 'wb') as fp:
            fp.write(contents.encode('utf-8'))


class Asset(Readable):
    """ A built-in asset identifier, created by using pkg_resources. """
    def read(self) -> str:
        """ Return a string with the UTF-8 text contents of a built-in asset as returned by assets_in_package. """
        resource_name = "/".join((_ASSETS_RESOURCE_PATH, self))
        return resource_string(_ASSETS_PACKAGE_PATH, resource_name).decode('utf-8')


def assets_in_package() -> List[Asset]:
    """ Return a list containing all files (not including path) from the built-in assets directory. """
    return [Asset(s) for s in resource_listdir(_ASSETS_PACKAGE_PATH, _ASSETS_RESOURCE_PATH)]


def dict_files_from_plover_cfg() -> List[File]:
    """ Attempt to find the local Plover installation and, if found, return a list containing all dictionary
        files in the correct priority order (reverse of normal, since earlier keys overwrite later ones). """
    cfg = configparser.ConfigParser()
    for path in _user_data_paths('plover'):
        cfg_path = os.path.join(path, "plover.cfg")
        if cfg.read(cfg_path):
            try:
                dict_section = cfg['System: English Stenotype']['dictionaries']
                dict_file_entries = reversed(json.loads(dict_section))
                return [File(os.path.join(path, d['path'])) for d in dict_file_entries]
            except KeyError:
                print("Could not find dictionaries in plover.cfg.")
            except json.decoder.JSONDecodeError:
                print("Problem decoding JSON in plover.cfg.")
    return []


def _user_data_paths(appname:str) -> List[str]:
    """ Directories to search for an application's configuration/assets in user space. """
    paths = [os.path.join(os.path.expanduser('~'), "AppData", "Local", appname),    # Windows
             os.path.join(os.path.expanduser('~'), "AppData", "Roaming", appname),  # Windows
             os.path.expanduser('~/Library/Application Support/'),                  # Mac
             os.getenv('XDG_DATA_HOME', os.path.expanduser("~/.local/share"))]      # Linux
    return [os.path.join(path, appname) for path in paths if path is not None]


def get_extension(name:str) -> str:
    """ Return only the extension of the given filename or resource, including the dot.
        Will return an empty string if there is no extension (such as with a directory). """
    return os.path.splitext(name)[1]
