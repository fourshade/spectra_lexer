from typing import List, Union

from spectra_lexer import on, pipe, respond_to, SpectraComponent
from spectra_lexer.dict.rule_dict import StenoRuleParser
from spectra_lexer.dict.steno_dict import StenoSearchDictionary

# Data types for (key, value) pairs in a raw dict to determine which kind it is.
DICT_TYPES = {(str, list): "rules",
              (str, str):  "translations"}


class IdentityParser:
    """ If a dict is usable straight from JSON with no modifications, use this do-nothing parser. """
    def __getattr__(self, attr):
        return lambda d: d


# Parsers for each raw dict type. Each should possess the methods "from_raw" and "to_raw".
DICT_PARSERS = {"rules":        StenoRuleParser,
                "translations": IdentityParser}


class DictManager(SpectraComponent):
    """ Handles all conversion required between raw dicts loaded straight from JSON and custom data structures.
        Stores all loaded rules/steno dicts and provides search engine services to the GUI and lexer. """

    parsers: dict
    translations: StenoSearchDictionary  # Search dict between strokes <-> translations.

    def __init__(self):
        """ Create each parser, filling in an identity function for each type that does not need parsing. """
        super().__init__()
        self.parsers = {k: v() for (k, v) in DICT_PARSERS.items()}
        self.translations = StenoSearchDictionary()

    @on("new_raw_dict")
    def parse_dict(self, raw_dict:dict):
        """ Determine the type of the dict from the first item and call the right parser. """
        if not raw_dict:
            raise ValueError("Got an empty raw dict. Cannot determine type.")
        key, value = next(iter(raw_dict.items()))
        d_type = DICT_TYPES.get((type(key), type(value)))
        if not d_type:
            raise TypeError("Got a raw dict with undecodable type.")
        d = self.parsers[d_type].from_raw(raw_dict)
        self.engine_call("new_"+d_type, d)
        return d

    @pipe("dict_save", "file_save", unpack=True)
    def save_dict(self, d_type:str, filename:str, obj) -> tuple:
        """ Convert a resource into a JSON dict using the previous parser as reference and save it to disk. """
        return filename, self.parsers[d_type].to_raw(obj)

    @on("new_translations")
    def new_search_dict(self, d:dict) -> None:
        """ Create translation dictionaries to search in either direction from the raw steno dictionary given. """
        self.translations = StenoSearchDictionary(d)

    @respond_to("search_lookup")
    def get(self, match, from_dict:str="forward") -> Union[str, List[str]]:
        """ Perform a simple lookup as with dict.get. """
        return self.translations.get(match, from_dict)

    @respond_to("search_special")
    def search(self, pattern:str, count:int=None, from_dict:str="forward", regex:bool=False) -> List[str]:
        """ Perform a special search for <pattern> with the given dict and mode. Return up to <count> matches. """
        return self.translations.search(pattern, count, from_dict, regex)
