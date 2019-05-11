from functools import partial
from typing import Callable, Iterable, List

from spectra_lexer.core import Component


class SearchPanel(Component):

    # Engine commands in order that must be connected for a responsive GUI, on these actions:
    COMMAND_KEYS = ["search_input",          # The string in the search input box has changed.
                    "search_choose_match",   # The user has chosen an item in the upper matches list.
                    "search_choose_mapping", # The user has chosen an item in the lower mappings list.
                    "search_mode_strokes",   # The check box has changed state between word search and stroke search.
                    "search_mode_regex"]     # The check box has changed state between prefix and regex search.

    def connect_all(self, connectors:Iterable[Callable]) -> None:
        """ Connect all search actions to engine commands in the order listed above. """
        for connector, cmd_key in zip(connectors, self.COMMAND_KEYS):
            connector(partial(self.engine_call, cmd_key))

    @on("new_search_input")
    def set_input(self, text:str) -> None:
        """ The program has manually changed the search input text. """
        raise NotImplementedError

    @on("new_search_match_list")
    def set_matches(self, str_list:List[str]) -> None:
        """ The program needs to show a new list of strings in the matches list. """
        raise NotImplementedError

    @on("new_search_match_selection")
    def select_matches(self, key:str) -> None:
        """ The program has manually selected an entry in the matches list by string value. """
        raise NotImplementedError

    @on("new_search_mapping_list")
    def set_mappings(self, str_list:List[str]) -> None:
        """ The program needs to show a new list of strings in the mappings list. """
        raise NotImplementedError

    @on("new_search_mapping_selection")
    def select_mappings(self, key:str) -> None:
        """ The program has manually selected an entry in the mappings list by string value. """
        raise NotImplementedError
