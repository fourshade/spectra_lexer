from functools import partial
from typing import Callable, Iterable, List

from spectra_lexer.core import Component


class SearchPanel(Component):

    COMMAND_KEYS = ["search_input",
                    "search_choose_match",
                    "search_choose_mapping",
                    "search_mode_strokes",
                    "search_mode_regex"]

    def connect_all(self, connectors:Iterable[Callable]) -> None:
        """ Connect all search actions to engine commands. """
        for connector, cmd_key in zip(connectors, self.COMMAND_KEYS):
            connector(partial(self.engine_call, cmd_key))

    @on("new_search_input")
    def set_input(self, text:str) -> None:
        raise NotImplementedError

    @on("new_search_match_list")
    def set_matches(self, str_list:List[str]) -> None:
        raise NotImplementedError

    @on("new_search_match_selection")
    def select_matches(self, key:str) -> None:
        raise NotImplementedError

    @on("new_search_mapping_list")
    def set_mappings(self, str_list:List[str]) -> None:
        raise NotImplementedError

    @on("new_search_mapping_selection")
    def select_mappings(self, key:str) -> None:
        raise NotImplementedError
