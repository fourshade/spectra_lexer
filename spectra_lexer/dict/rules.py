from typing import Iterable, List, Tuple

from spectra_lexer import on, fork, pipe, Component
from spectra_lexer.dict.rule_parser import StenoRuleParser
from spectra_lexer.utils import merge

# Resource glob pattern for the built-in JSON-based rules files.
_RULES_ASSET_PATTERN = "*.cson"


class RulesManager(Component):

    rule_parser: StenoRuleParser  # Rule parser that tracks reference names in case we want to save new rules.

    @on("start")
    def start(self, **opts):
        """ Create all parsers and load them with command line arguments. """
        self.rule_parser = StenoRuleParser()

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
