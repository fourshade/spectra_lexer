""" Module for raw I/O operations as well as parsing file and resource paths. """

import fnmatch
import glob
import os
import re

from appdirs import user_data_dir
from pkg_resources import resource_listdir, resource_string

from spectra_lexer.utils import abstract_method, str_prefix

# Package and resource paths containing built-in assets.
_PACKAGE_NAME = str_prefix(__package__, ".")
_ASSETS_RESOURCE_PATH = "assets"
# Prefixes and delimiters for specifying special places to look.
_ASSET_DELIMITER = "/"
_ASSET_PREFIX = ":/"
_USER_PATTERN = re.compile(r"~(.*?)/")


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
        """ Write the given string as the sole contents of a UTF-8 text file.
            If the directory path doesn't exist, create it. """
        directory = os.path.dirname(self)
        os.makedirs(directory, exist_ok=True)
        with open(self, 'wb') as fp:
            fp.write(contents.encode('utf-8'))

    @classmethod
    def glob(cls, pattern:str) -> list:
        """ Return a list containing resources matching the pattern from the filesystem. """
        return [cls(f) for f in glob.glob(pattern)]


class Asset(Resource):
    """ A built-in asset identifier, created by using pkg_resources. """

    def read(self) -> str:
        """ Return a string with the UTF-8 text contents of a built-in asset as returned by assets_in_package. """
        resource_name = _ASSET_DELIMITER.join((_ASSETS_RESOURCE_PATH, self))
        return resource_string(_PACKAGE_NAME, resource_name).decode('utf-8')

    def write(self, contents:str) -> None:
        raise TypeError("Writing of built-in assets not supported.")

    @classmethod
    def glob(cls, pattern:str) -> list:
        """ Return a list containing resources matching the pattern from the built-in assets directory. """
        asset_list = resource_listdir(_PACKAGE_NAME, _ASSETS_RESOURCE_PATH)
        return [cls(_ASSET_PREFIX + f) for f in fnmatch.filter(asset_list, pattern)]


def string_to_resource(filename:str) -> Resource:
    """ Given a string, determine the type of resource from the prefix and create the appropriate identifier.
        If the prefix is ~appname/, it is a file from the user's application-specific data directory.
        If the prefix is ~/, it is specifically a file from THIS application's user data directory.
        If the prefix is :/, it is a built-in asset. In any other case it is an ordinary file. """
    if _USER_PATTERN.match(filename):
        return _get_user_file(filename)
    if filename.startswith(_ASSET_PREFIX):
        return Asset(filename[2:])
    return File(filename)


def _get_user_file(filename:str) -> File:
    """ Get an identifier for a file in the user's app data directory. """
    _, appname, f = _USER_PATTERN.split(filename, 1)
    directory = user_data_dir(appname or _PACKAGE_NAME)
    return File(os.path.join(directory, f))
