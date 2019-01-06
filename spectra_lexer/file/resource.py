""" Module for raw I/O operations as well as parsing file and resource paths. """

import fnmatch
import glob
import os
from typing import List

from appdirs import user_data_dir
from pkg_resources import resource_listdir, resource_string

from spectra_lexer.utils import abstract_method

# Package and resource paths containing built-in assets.
_ASSETS_PACKAGE_PATH: str = __name__.split(".", 1)[0]
_ASSETS_RESOURCE_PATH: str = "assets"

# Pre-expanded path to the user's data directory.
_USER_DATA_PATH = user_data_dir('spectra_lexer')


class Resource(str):
    """ Marker class for a resource identifier. """
    read = abstract_method
    write = abstract_method


class File(Resource):
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


class Asset(Resource):
    """ A built-in asset identifier, created by using pkg_resources. """
    def read(self) -> str:
        """ Return a string with the UTF-8 text contents of a built-in asset as returned by assets_in_package. """
        resource_name = "/".join((_ASSETS_RESOURCE_PATH, self))
        return resource_string(_ASSETS_PACKAGE_PATH, resource_name).decode('utf-8')

    def write(self, contents:str) -> None:
        raise AttributeError("Writing of built-in assets not supported.")


def glob_files(pattern:str) -> List[File]:
    """ Return a list containing resources matching the pattern from the filesystem. """
    return [File(f) for f in glob.glob(pattern)]


def glob_assets(pattern:str) -> List[Asset]:
    """ Return a list containing resources matching the pattern from the built-in assets directory. """
    asset_list = resource_listdir(_ASSETS_PACKAGE_PATH, _ASSETS_RESOURCE_PATH)
    return [Asset(f) for f in fnmatch.filter(asset_list, pattern)]


def user_data_file(filename:str, *, appname:str=None) -> File:
    """ Return a full path to a file in the user's home directory.
        If no program name is given, it is assumed to be a request for this program's files. """
    directory = user_data_dir(appname) if appname is not None else _USER_DATA_PATH
    return File(os.path.join(directory, filename))
