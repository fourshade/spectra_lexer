from typing import Any, Iterable, List

from spectra_lexer import Component, on, respond_to
from spectra_lexer.file.codecs import DECODERS, decode_resource, ENCODERS, encode_resource
from spectra_lexer.file.resource import Asset, File, string_to_resource


class FileHandler(Component):
    """ Engine wrapper for file I/O operations. Directs engine commands to module-level functions. """

    @respond_to("file_list")
    def list_files(self, pattern:str) -> List[File]:
        """ Return a list containing all filenames that match the given glob pattern. """
        return File.glob(pattern)

    @respond_to("file_list_assets")
    def list_assets(self, pattern:str) -> List[Asset]:
        """ Return a list containing all built-in assets that match the given glob pattern. """
        return Asset.glob(pattern)

    @respond_to("file_load")
    def load_resource(self, filename:str) -> Any:
        """ Attempt to decode a resource from a file or asset given by name. """
        f = string_to_resource(filename)
        return decode_resource(f)

    @on("file_save")
    def save_resource(self, filename:str, obj:Any) -> None:
        """ Attempt to encode and save a resource to a file given by name. """
        f = string_to_resource(filename)
        return encode_resource(f, obj)

    @respond_to("file_get_decodable_exts")
    def get_decodable_exts(self) -> Iterable[str]:
        """ Return all valid file extensions (including the dot) for decodable dictionaries. """
        return DECODERS.keys()

    @respond_to("file_get_encodable_exts")
    def get_encodable_exts(self) -> Iterable[str]:
        """ Return all valid file extensions (including the dot) for encodable dictionaries. """
        return ENCODERS.keys()
