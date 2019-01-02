from typing import Union, List

from spectra_lexer import SpectraComponent, on, respond_to
from spectra_lexer.search.steno_dict import StenoSearchDictionary


class SearchEngine(SpectraComponent):
    """ Provides steno translation search engine services to the GUI and lexer. """

    translations: StenoSearchDictionary  # Search dict between strokes <-> translations.

    def __init__(self):
        super().__init__()
        self.translations = StenoSearchDictionary()

    @on("new_translations")
    def new_search_dict(self, d:dict) -> None:
        """ Create a master dictionary to search in either direction from the raw translations dict given. """
        self.translations = StenoSearchDictionary(d)

    @respond_to("search_lookup")
    def get(self, match, from_dict:str="forward") -> Union[str, List[str]]:
        """ Perform a simple lookup as with dict.get. """
        return self.translations.get(match, from_dict)

    @respond_to("search_special")
    def search(self, pattern:str, count:int=None, from_dict:str="forward", regex:bool=False) -> List[str]:
        """ Perform a special search for <pattern> with the given dict and mode. Return up to <count> matches. """
        return self.translations.search(pattern, count, from_dict, regex)
