from typing import Any, Iterable, List

from spectra_lexer import Component, on, respond_to
from spectra_lexer.file.codecs import DECODERS, decode_resource, ENCODERS, encode_resource
from spectra_lexer.file.resource import Asset, File, glob_assets, glob_files, user_data_file


class FileHandler(Component):
    """ Engine wrapper for file I/O operations. Directs engine commands to module-level functions. """

    @respond_to("file_list")
    def list_files(self, pattern:str) -> List[File]:
        """ Return a list containing all filenames that match the given glob pattern. """
        return glob_files(pattern)

    @respond_to("file_load")
    def load_file(self, filename:str) -> Any:
        """ Attempt to decode a resource from a file given by name. """
        return decode_resource(File(filename))

    @on("file_save")
    def save_file(self, filename:str, obj:Any) -> None:
        """ Attempt to encode and save a resource to a file given by name. """
        return encode_resource(File(filename), obj)

    @respond_to("file_list_assets")
    def list_assets(self, pattern:str) -> List[Asset]:
        """ Return a list containing all built-in assets that match the given glob pattern. """
        return glob_assets(pattern)

    @respond_to("file_load_asset")
    def load_asset(self, rname:str) -> Any:
        """ Attempt to decode a built-in resource given by name. """
        return decode_resource(Asset(rname))

    @respond_to("file_load_user")
    def load_user(self, filename:str, *, appname:str=None) -> Any:
        """ Attempt to decode a resource from the user's application-specific data directory.
            <appname> defaults to this program unless otherwise specified. """
        return decode_resource(user_data_file(filename, appname=appname))

    @on("file_save_user")
    def save_user(self, filename:str, obj:Any) -> None:
        """ Attempt to encode and save a resource to the user's Spectra data directory.
            Unlike load_user, we assume we will not be saving over another app's data. """
        return encode_resource(user_data_file(filename), obj)

    @respond_to("file_get_decodable_exts")
    def get_decodable_exts(self) -> Iterable[str]:
        """ Return all valid file extensions (including the dot) for decodable dictionaries. """
        return DECODERS.keys()

    @respond_to("file_get_encodable_exts")
    def get_encodable_exts(self) -> Iterable[str]:
        """ Return all valid file extensions (including the dot) for encodable dictionaries. """
        return ENCODERS.keys()
