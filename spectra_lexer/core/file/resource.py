""" Module for raw I/O operations as well as parsing file and resource paths. """

import fnmatch
import glob
import os
import re

from appdirs import user_data_dir
from pkg_resources import resource_listdir, resource_string

from spectra_lexer.utils import str_prefix

# Package and resource paths containing built-in assets.
_PACKAGE_NAME = str_prefix(__package__, ".")
_ASSETS_RESOURCE_PATH = "assets"
_ASSET_LIST = resource_listdir(_PACKAGE_NAME, _ASSETS_RESOURCE_PATH)

# Prefixes and patterns for specifying special places to look.
_ASSET_PREFIX = ":/"
_USER_PATTERN = re.compile(r"~(.*?)/")


class Resource(str):
    """ Abstract class for a resource identifier. """

    def read(self) -> str:
        raise NotImplementedError

    def write(self, contents:str) -> None:
        raise NotImplementedError

    def glob(self) -> list:
        raise NotImplementedError


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
        directory = os.path.dirname(self) or "."
        os.makedirs(directory, exist_ok=True)
        with open(self, 'wb') as fp:
            fp.write(contents.encode('utf-8'))

    def glob(self) -> list:
        """ Return a list containing resources matching the identifier from the filesystem. """
        return [File(f) for f in glob.glob(self)]


class Asset(Resource):
    """ A built-in asset identifier, created by using pkg_resources. """

    def __new__(cls, s:str):
        """ If the prefix is :/, it is a built-in asset. Otherwise it is an ordinary file. """
        if s.startswith(_ASSET_PREFIX):
            return super().__new__(cls, s[len(_ASSET_PREFIX):])
        return None

    def read(self) -> str:
        """ Return a string with the UTF-8 text contents of a built-in asset as returned by assets_in_package. """
        resource_name = _ASSET_PREFIX[-1].join((_ASSETS_RESOURCE_PATH, self))
        return resource_string(_PACKAGE_NAME, resource_name).decode('utf-8')

    def write(self, contents:str) -> None:
        raise TypeError("Writing of built-in assets not supported.")

    def glob(self) -> list:
        """ Return a list containing resources matching the identifier from the built-in assets directory. """
        return [Asset(_ASSET_PREFIX + f) for f in fnmatch.filter(_ASSET_LIST, self)]


class UserFile(File):
    """ An identifier for a file in the user's app data directory. """

    def __new__(cls, s:str):
        """ If the prefix is ~appname/, it is a file from the user's application-specific data directory.
            If the prefix is ~/, it is specifically a file from THIS application's user data directory. """
        if _USER_PATTERN.match(s):
            _, appname, filename = _USER_PATTERN.split(s, 1)
            directory = user_data_dir(appname or _PACKAGE_NAME)
            return super().__new__(cls, os.path.join(directory, filename))
        return None


def resource_from_string(s:str) -> Resource:
    """ Given a string, determine the type of resource from the prefix and create the appropriate identifier. """
    return UserFile(s) or Asset(s) or File(s)  # Ordinary file resource creation will always succeed.


def resources_from_patterns(*patterns:str) -> list:
    """ Given strings, determine the resource types from the prefix and expand the patterns into a list. """
    return [m for p in patterns for m in resource_from_string(p).glob()]
