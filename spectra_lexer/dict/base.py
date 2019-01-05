from functools import wraps
from typing import Any, Sequence

from spectra_lexer import pipe, SpectraComponent
from spectra_lexer.dict.rule_parser import StenoRuleParser


def type_check_items(types:Sequence[type]) -> callable:
    """ Raise an error if the first item in the dict does not match the given types. Empty dicts are given a pass. """
    def type_check_deco(func:callable) -> callable:
        @wraps(func)
        def parse_if_correct(self, raw_dict:dict) -> Any:
            if raw_dict:
                test_item = next(iter(raw_dict.items()))
                if not all(map(isinstance, test_item, types)):
                    raise TypeError(f"Invalid input dict format.")
            return func(self, raw_dict)
        return parse_if_correct
    return type_check_deco


class DictManager(SpectraComponent):
    """ Handles all conversion required between raw dicts loaded straight from JSON and custom data structures. """

    rule_parser: StenoRuleParser  # Rule parser that tracks reference names in case we want to save new rules.

    def __init__(self):
        super().__init__()
        self.rule_parser = StenoRuleParser()

    @pipe("new_raw_rules", "new_rules")
    @type_check_items([str, list])
    def parse_rules(self, raw_dict:dict) -> list:
        """ Parse rules from a JSON dict and return only a list (without the reference names). """
        return self.rule_parser.from_raw(raw_dict)

    @pipe("dict_save_rules", "file_save", unpack=True)
    def save_rules(self, filename:str, obj:Any) -> tuple:
        """ Parse rules from an object into raw form using reference data from the parser, then save them. """
        return filename, self.rule_parser.to_raw(obj)
