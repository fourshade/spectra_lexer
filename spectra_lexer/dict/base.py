from typing import List, Union

from spectra_lexer import on, pipe, respond_to, SpectraComponent
from spectra_lexer.dict.rule_dict import StenoRuleDict
from spectra_lexer.dict.steno_dict import StenoSearchDictionary


class DictManager(SpectraComponent):
    """ Handles all conversion required between raw dicts loaded straight from JSON and custom data structures.
        Stores all loaded rules/steno dicts and provides search engine services to the GUI and lexer. """

    rules: StenoRuleDict                 # Steno rule dict with reference keys.
    translations: StenoSearchDictionary  # Search dict between strokes <-> translations.

    def __init__(self):
        super().__init__()
        self.rules = StenoRuleDict()
        self.translations = StenoSearchDictionary()

    @on("new_raw_dict")
    def parse_dict(self, raw_dict:dict) -> None:
        """ Determine the type of items in the dict from the first item and call the right parsing method. """
        if not raw_dict:
            raise ValueError("Got an empty dict. Cannot determine type.")
        key, value = next(iter(raw_dict.items()))
        if isinstance(value, str):
            self.engine_send("dict_parse_translations", raw_dict)
        else:
            self.engine_send("dict_parse_rules", raw_dict)

    @pipe("dict_parse_rules", "new_rules")
    def parse_rules(self, raw_dict:dict) -> list:
        """ Parse the rules and save the dict. Then send the rules in a list. The lexer does not need the names. """
        d = self.rules = StenoRuleDict(raw_dict)
        return list(d.values())

    @pipe("dict_parse_translations", "new_search_dict")
    def parse_translations(self, raw_dict:dict) -> StenoSearchDictionary:
        """ Create the translation dictionaries from the raw steno dictionary given and show a success message.
            Keys are RTFCRE stroke strings, values are English text translations. No further parsing is needed.
            Create dicts to search in either direction and process requests. """
        d = self.translations = StenoSearchDictionary(raw_dict)
        return d

    @respond_to("search_lookup")
    def get(self, match, from_dict:str="forward") -> Union[str, List[str]]:
        """ Perform a simple lookup as with dict.get. """
        return self.translations.get(match, from_dict)

    @respond_to("search_special")
    def search(self, pattern:str, count:int=None, from_dict:str="forward", regex:bool=False) -> List[str]:
        """ Perform a special search for <pattern> with the given dict and mode. Return up to <count> matches. """
        return self.translations.search(pattern, count, from_dict, regex)
