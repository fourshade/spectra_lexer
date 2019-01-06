from typing import Any, Iterable

from spectra_lexer import Component, fork, on, respond_to
from spectra_lexer.file.codecs import DECODERS, decode_resource, ENCODERS, encode_resource
from spectra_lexer.file.path import config_from_user_data, dict_files_from_plover_cfg, rules_from_assets_dir
from spectra_lexer.file.resource import File, Resource
from spectra_lexer.utils import merge


class FileHandler(Component):
    """ Engine wrapper for file I/O operations. Directs engine commands to module-level functions. """

    @fork("file_load_config", "new_config")
    def load_config(self) -> dict:
        """ Load the config file (if present) from the user directory. """
        f = config_from_user_data()
        return decode_resource(f) if f else {}

    @on("file_save_config")
    def save_config(self, d:dict) -> None:
        """ Save the config file to the user directory. """
        encode_resource(config_from_user_data(), d)

    @fork("file_load_builtin_rules", "new_raw_rules")
    def load_initial_rules(self) -> dict:
        """ Load and merge the rules from the built-in asset directories. """
        return decode_and_merge(rules_from_assets_dir())

    @fork("file_load_plover_dicts", "new_translations")
    def load_initial_translations(self) -> dict:
        """ Make an attempt to locate Plover's dictionaries and load/merge those. """
        return decode_and_merge(dict_files_from_plover_cfg())

    @respond_to("file_load")
    def load_file(self, filename:str) -> Any:
        """ Attempt to decode a resource from a file given by name. """
        return decode_resource(File(filename))

    @on("file_save")
    def save_file(self, filename:str, obj:Any) -> None:
        """ Attempt to encode a resource to a file given by name and save it. """
        return encode_resource(File(filename), obj)

    @respond_to("file_get_decodable_exts")
    def get_decodable_exts(self) -> Iterable[str]:
        """ Return all valid file extensions (including the dot) for decodable dictionaries. """
        return DECODERS.keys()

    @respond_to("file_get_encodable_exts")
    def get_encodable_exts(self) -> Iterable[str]:
        """ Return all valid file extensions (including the dot) for encodable dictionaries. """
        return ENCODERS.keys()


def decode_and_merge(f_names:Iterable[Resource]=()) -> dict:
    """ Load each dictionary from a resource identifier and merge them all. """
    return merge(decode_resource(f) for f in f_names)
