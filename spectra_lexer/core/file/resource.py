""" Module for raw I/O operations as well as parsing file and resource paths. """

import fnmatch
import glob
import os

from appdirs import user_data_dir
from pkg_resources import resource_listdir, resource_string

from spectra_lexer.utils import str_prefix

# Universal path separator. Built-in asset names use this independently of OS path handling.
_PATH_SEP = "/"
# Package and resource paths containing built-in assets.
_PACKAGE_NAME = str_prefix(__package__, ".")
_ASSETS_RESOURCE_PATH = "assets"
_ASSET_LIST = resource_listdir(_PACKAGE_NAME, _ASSETS_RESOURCE_PATH)


class Resource(str):
    """ Abstract class for a resource identifier. """

    _TYPES: list = []  # Resource types to check for membership, in order.

    def __init_subclass__(cls, prefix:str=""):
        """ Add a new resource subclass to the list and sort by prefix in reverse so longer ones are tried first. """
        cls._TYPES.append((prefix, cls))
        cls._TYPES.sort(reverse=True)

    @classmethod
    def from_string(cls, s:str):
        """ Given a string, determine the type of resource from the prefix and create the appropriate identifier. """
        for prefix, tp in cls._TYPES:
            if s.startswith(prefix):
                return tp(s[len(prefix):])

    @classmethod
    def from_pattern(cls, pattern:str) -> list:
        """ Given a string, determine the resource type from the prefix and expand the pattern into a list. """
        return cls.from_string(pattern).search()

    @classmethod
    def from_list(cls, str_list:list) -> list:
        """ Given a list of strings, make a list of resources from *this* class and return it. """
        return [cls(s) for s in str_list]

    def read(self) -> str:
        raise TypeError("Reading of this resource type is not supported.")

    def write(self, contents:str) -> None:
        raise TypeError("Writing of this resource type is not supported.")

    def search(self) -> list:
        return []


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

    def search(self) -> list:
        """ Return a list containing resources matching the identifier from the filesystem. """
        return self.from_list(glob.glob(self))


class Asset(Resource, prefix=":/"):
    """ A built-in asset identifier, created by using pkg_resources. """

    def read(self) -> str:
        """ Return a string with the UTF-8 text contents of a built-in asset as returned by assets_in_package. """
        resource_name = _PATH_SEP.join((_ASSETS_RESOURCE_PATH, self))
        return resource_string(_PACKAGE_NAME, resource_name).decode('utf-8')

    def search(self) -> list:
        """ Return a list containing resources matching the identifier from the built-in assets directory. """
        return self.from_list(fnmatch.filter(_ASSET_LIST, self))


class UserFile(File, prefix="~"):
    """ An identifier for a file in the user's app data directory. Produces instances of its superclass only. """

    def __new__(cls, s:str):
        """ If the prefix is ~appname/, it is a file from the user's application-specific data directory.
            If the prefix is ~/, it is specifically a file from THIS application's user data directory. """
        app_prefix, filename = s.split(_PATH_SEP, 1)
        directory = user_data_dir(app_prefix or _PACKAGE_NAME)
        return File(os.path.join(directory, filename))


class Null(Resource, prefix="NUL"):
    """ A dummy class that reads nothing and writes to a black hole. """

    read = lambda self: ""
    write = lambda *args: None
