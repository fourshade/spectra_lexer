from typing import Dict, Iterable, List

from spectra_lexer import SpectraComponent
from spectra_lexer.file.codecs import decode_assets, decode_files, DECODERS
from spectra_lexer.file.io_path import assets_in_package, dict_files_from_plover_cfg
from spectra_lexer.file.parser import StenoRuleDict
from spectra_lexer.rules import StenoRule


class FileHandler(SpectraComponent):
    """ Engine wrapper for file I/O operations. Directs engine commands to module-level functions. """

    def engine_commands(self) -> dict:
        """ Individual components must define the signals they respond to and the appropriate callbacks. """
        return {**super().engine_commands(),
                "file_load_steno_dicts": (self.load_steno_dicts, "search_set_dict"),
                "file_load_rules_dicts": (self.load_rule_dicts,  "lexer_set_rules"),
                "file_get_dict_formats": (DECODERS.keys,         "gui_open_file_dialog")}

    @staticmethod
    def load_rule_dicts(filenames:Iterable[str]=()) -> List[StenoRule]:
        """ Attempt to load one or more rules dictionaries given by filename.
            If none were given, attempt to load the built-in rules files.
            Parse them into a finished dict and keep a copy in memory.
            Send only the rules (not the names) in a list to the lexer. """
        if filenames:
            raw_dict = merge(decode_files(filenames))
        else:
            raw_dict = merge(decode_assets(assets_in_package()))
        rule_dict = StenoRuleDict(raw_dict)
        return list(rule_dict.values())

    @staticmethod
    def load_steno_dicts(filenames:Iterable[str]=()) -> Dict[str, str]:
        """ Attempt to load one or more steno dictionaries given by filename.
            If none were given, attempt to locate Plover's dictionaries and load those.
            Keys are RTFCRE stroke strings, values are English text translations. """
        filenames = filenames or dict_files_from_plover_cfg()
        return merge(decode_files(filenames))


def merge(d_iter:Iterable[dict]) -> dict:
    """ Merge one or more dicts, overwriting earlier entries if keys are duplicated. """
    merged = {}
    for d in d_iter:
        merged.update(d)
    return merged
