import json
from typing import Iterable, Mapping, Tuple, List

from spectra_lexer import Component, fork, pipe, on
from spectra_lexer.dict.config import ConfigManager
from spectra_lexer.dict.rule_parser import StenoRuleParser
from spectra_lexer.utils import merge

# Resource glob pattern for the built-in JSON-based rules files.
_RULES_ASSET_PATTERN = "*.cson"


class DictManager(Component):
    """ Handles all conversion and merging required for file operations on specific types of dicts. """

    rule_parser: StenoRuleParser  # Rule parser that tracks reference names in case we want to save new rules.
    config_parser: ConfigManager  # Configuration manager that tracks where we want our config saved.

    @on("start")
    def from_raw(self, cfg:str=None, **opts):
        """ Create all parsers and load them with command line arguments. """
        self.rule_parser = StenoRuleParser()
        self.config_parser = ConfigManager(cfg)

    @fork("dict_load_config", "new_config_data")
    def load_config(self, filenames:Iterable[str]=None) -> dict:
        """ Load and merge all config options from disk. Ignore failures and convert strings using AST. """
        if filenames is None:
            filenames = [self.config_parser.cfg_file]
        try:
            dicts = [self.engine_call("file_load", f) for f in filenames]
        except OSError:
            dicts = []
        return self.config_parser.from_raw(merge(dicts))

    @pipe("dict_save_config", "file_save", unpack=True)
    def save_config(self, cfg_data:dict, filename:str=None) -> Tuple[str, dict]:
        """ Save config options to disk. Saving should not fail silently, unlike loading. """
        if filename is None:
            filename = self.config_parser.cfg_file
        return filename, self.config_parser.to_raw(cfg_data)

    @fork("dict_load_rules", "new_rules")
    def load_rules(self, filenames:Iterable[str]=None) -> list:
        """ Load and merge every rules dictionary given. If none are given, use the built-in assets.
            Parse the rules and return only a list (without the reference names). """
        if filenames is not None:
            rules_dicts = [self.engine_call("file_load", f) for f in filenames]
        else:
            rules_dicts = self._decode_builtin_rules()
        return self.rule_parser.from_raw(merge(rules_dicts))

    def _decode_builtin_rules(self) -> List[dict]:
        """ Decode every JSON rules file from the built-in assets directory. """
        asset_names = self.engine_call("file_list_assets", _RULES_ASSET_PATTERN)
        return [self.engine_call("file_load", f) for f in asset_names]

    @pipe("dict_save_rules", "file_save", unpack=True)
    def save_rules(self, filename:str, rules:Iterable) -> Tuple[str, dict]:
        """ Parse rules from an object into raw form using reference data from the parser, then save them. """
        return filename, self.rule_parser.to_raw(rules)

    @fork("dict_load_translations", "new_translations")
    def load_translations(self, filenames:Iterable[str]=None) -> dict:
        """ Load and merge every translation dictionary given.
            If none are given, attempt to find dictionaries belonging to a Plover installation and load those. """
        if filenames is not None:
            dicts = [self.engine_call("file_load", f) for f in filenames]
        else:
            dicts = self._decode_plover_cfg_translations()
        return merge(dicts)

    def _decode_plover_cfg_translations(self) -> List[dict]:
        """ Attempt to find the local Plover user directory and, if found, decode all dictionary files
            in the correct priority order (reverse of normal, since earlier keys overwrite later ones). """
        try:
            cfg_dict = self._get_plover_file("plover.cfg")
            dict_section = cfg_dict['System: English Stenotype']['dictionaries']
            # The section we need is read as a string, but it must be decoded as a JSON array.
            dict_filenames = [e['path'] for e in reversed(json.loads(dict_section))]
            return [self._get_plover_file(f) for f in dict_filenames]
        except OSError:
            # Catch-all for file loading errors. Just assume the required files aren't there and move on.
            pass
        except KeyError:
            print("Could not find dictionaries in plover.cfg.")
        except json.decoder.JSONDecodeError:
            print("Problem decoding JSON in plover.cfg.")
        return []

    def _get_plover_file(self, filename:str) -> dict:
        """ Get a file from the Plover user directory. If it doesn't exist, make sure we get the exception. """
        return self.engine_call("file_load", "~plover/" + filename)

    @pipe("dict_save_translations", "file_save", unpack=True)
    def save_translations(self, filename:str, translations:Mapping) -> Tuple[str, Mapping]:
        """ Not strictly necessary; the file handler will work directly for this, but it preserves uniformity. """
        return filename, translations
