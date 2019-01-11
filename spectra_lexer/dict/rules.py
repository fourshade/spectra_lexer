from typing import List

from spectra_lexer.dict.manager import ResourceManager
from spectra_lexer.dict.rule_parser import StenoRuleParser

# Resource glob pattern for the built-in JSON-based rules files.
_RULES_ASSET_PATTERN = ":/*.cson"


class RulesManager(ResourceManager):

    CMD_SUFFIX = "rules"
    OPT_KEY = "rules"
    rule_parser: StenoRuleParser  # Rule parser that tracks reference names in case we want to save new rules.

    def __init__(self):
        super().__init__()
        self.rule_parser = StenoRuleParser()

    def load_default(self) -> List[dict]:
        """ Decode every JSON rules file from the built-in assets directory. """
        return self.engine_call("file_load", _RULES_ASSET_PATTERN)

    def parse(self, d:dict) -> list:
        """ Parse the rules and return only a list (without the reference names). """
        return self.rule_parser.from_raw(d)

    def inv_parse(self, rules:list) -> dict:
        """ Parse rules from an object into raw form using reference data from the parser. """
        return self.rule_parser.to_raw(rules)
