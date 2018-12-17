from typing import Iterable

from spectra_lexer import on, SpectraComponent
from spectra_lexer.file.codecs import decode_assets, decode_files, DECODERS
from spectra_lexer.file.io_path import assets_in_package, dict_files_from_plover_cfg
from spectra_lexer.file.parser import StenoRuleDict
from spectra_lexer.utils import merge


class FileHandler(SpectraComponent):
    """ Engine wrapper for file I/O operations. Directs engine commands to module-level functions. """

    @on("start")
    def load_initial(self, rules_files:Iterable[str]=(), dict_files:Iterable[str]=None, **kwargs) -> None:
        """ Initial resource load upon startup. Arguments come from the command line. """
        # If <rules_files> is given as a parameter, load the rules files inside it and send them to the lexer.
        # If the parameter is empty or not given, load the rules from the built-in directories.
        self.load_rules(rules_files, "command line")
        # If <dict_files> is given as a parameter, try to load the steno dictionary files inside it on start-up.
        # If the parameter is given but empty, make an attempt to locate Plover's dictionaries and load those.
        # If the parameter is not given at all, do nothing. Some other component might provide the search dict.
        if dict_files is not None:
            self.load_translations(dict_files, "command line")

    @on("file_load_rules")
    def load_rules(self, filenames:Iterable[str]=(), src_string:str=None) -> list:
        """ Attempt to load one or more rules dictionaries given by filename. """
        if filenames:
            raw_dict = _decode_and_merge(filenames)
        else:
            # If no files were given, attempt to load the built-in rules files.
            raw_dict = _decode_and_merge(assets_in_package(), True)
            src_string = "built-in directory"
        # Gather the rules by themselves in a list. The lexer does not need the names.
        rules_list = list(StenoRuleDict(raw_dict).values())
        self._send_resource("new_rules", rules_list, "rules", src_string)
        # Return the resource in case this was a direct call.
        return rules_list

    @on("file_load_translations")
    def load_translations(self, filenames:Iterable[str]=(), src_string:str=None) -> dict:
        """ Attempt to load one or more steno translation dictionaries given by filename.
            Keys are RTFCRE stroke strings, values are English text translations. """
        if filenames:
            search_dict = _decode_and_merge(filenames)
        else:
            # If no files were given, attempt to locate Plover's dictionaries and load those.
            search_dict = _decode_and_merge(dict_files_from_plover_cfg())
            src_string = "Plover config"
        self._send_resource("new_search_dict", search_dict, "dictionaries", src_string)
        # Return the resource in case this was a direct call.
        return search_dict

    @on("file_get_decodable_exts")
    def get_decodable_exts(self):
        """ Return all valid file extensions (including the dot) for decodable dictionaries. """
        return DECODERS.keys()

    def _send_resource(self, command:str, resource, r_type:str, src_string:str) -> None:
        """ Send the new resource to the engine using <command> and show a status message. """
        self.engine_call(command, resource)
        if src_string is not None:
            self.engine_call("new_status", "Loaded {} from {}.".format(r_type, src_string))


def _decode_and_merge(r_names, asset_type=False):
    """ Decode and merge one or more dicts, overwriting earlier entries if keys are duplicated. """
    decode_fn = decode_assets if asset_type else decode_files
    return merge(decode_fn(r_names))
