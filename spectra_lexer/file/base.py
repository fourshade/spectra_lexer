from typing import Iterable

from spectra_lexer import fork, on, respond_to, SpectraComponent
from spectra_lexer.file.codecs import DECODERS, decode_resource, ENCODERS, encode_resource
from spectra_lexer.file.io_path import assets_in_package, dict_files_from_plover_cfg, File, Readable
from spectra_lexer.utils import merge


class FileHandler(SpectraComponent):
    """ Engine wrapper for file I/O operations. Directs engine commands to module-level functions. """

    @fork("file_load_builtin_rules", "new_raw_dict")
    def load_initial_rules(self) -> dict:
        """ Load and merge the rules from the built-in asset directories."""
        return decode_and_merge(assets_in_package())

    @fork("file_load_plover_dicts", "new_raw_dict")
    def load_initial_translations(self) -> dict:
        """ Make an attempt to locate Plover's dictionaries and load/merge those. """
        return decode_and_merge(dict_files_from_plover_cfg())

    @fork("file_load", "new_raw_dict")
    def load_file(self, filename:str) -> dict:
        """ Attempt to decode a dict from a file given by name. """
        return decode_resource(File(filename))

    @on("file_save")
    def save_file(self, filename:str, d:dict) -> None:
        """ Attempt to encode a dict to a file given by name and save it. """
        return encode_resource(File(filename), d)

    @respond_to("file_get_decodable_exts")
    def get_decodable_exts(self) -> Iterable[str]:
        """ Return all valid file extensions (including the dot) for decodable dictionaries. """
        return DECODERS.keys()

    @respond_to("file_get_encodable_exts")
    def get_encodable_exts(self) -> Iterable[str]:
        """ Return all valid file extensions (including the dot) for encodable dictionaries. """
        return ENCODERS.keys()


def decode_and_merge(f_names:Iterable[Readable]=()) -> dict:
    """ Load each dictionary from a resource identifier and merge them all. """
    return merge(decode_resource(f) for f in f_names)
