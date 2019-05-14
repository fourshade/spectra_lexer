from typing import List

from spectra_lexer.core import Command, Resource, Option
from spectra_lexer.steno import LX
from spectra_lexer.types.codec import CFGDict

ConfigDictionary = CFGDict
ConfigOption = Option()


class VIEW(LX):

    CONFIG: ConfigDictionary = Resource(ConfigDictionary())
    CONFIG_INFO: Option = ConfigOption  # Keeps track of configuration options in a master dict.

    @Command
    def VIEWConfigLoad(self, *patterns:str, **kwargs) -> ConfigDictionary:
        """ Load all config options from disk. Ignore missing files. """
        raise NotImplementedError

    @Command
    def VIEWConfigSave(self, cfg:ConfigDictionary, filename:str="", **kwargs) -> None:
        """ Update components and save all config options to disk. If no save filename is given, use the default. """
        raise NotImplementedError

    @Command
    def VIEWQuery(self, strokes:str, word:str) -> None:
        """ Execute and display a lexer query. """
        raise NotImplementedError

    @Command
    def board_resize(self, width:int, height:int) -> None:
        """ Tell the board layout engine when the graphical container changes size and redraw if necessary. """
        raise NotImplementedError

    @Command
    def graph_action(self, row:int, col:int, clicked:bool) -> None:
        """ Tell the graph engine when the mouse moves over a new character and/or is clicked. """
        raise NotImplementedError

    @Command
    def search_edit_input(self, pattern:str, **state) -> None:
        """ The string in the search input box has changed. Do a new search unless the input is blank. """
        raise NotImplementedError

    @Command
    def search_choose_match(self, pattern:str, match:str, **state) -> None:
        """ The user has chosen an item in the upper matches list. Do a lookup after special checks. """
        raise NotImplementedError

    @Command
    def search_choose_mapping(self, match:str, mapping:str, **state) -> None:
        """ The user has chosen an item in the lower mappings list. Send a display command. """
        raise NotImplementedError

    @Command
    def search_find_examples(self, rule_name:str, **state) -> None:
        """ When a link is clicked, search for examples of the named rule. """
        raise NotImplementedError

    @Command
    def VIEWNewTitle(self, title:str) -> None:
        raise NotImplementedError

    @Command
    def VIEWNewGraph(self, text:str, scroll_to:str="top") -> None:
        raise NotImplementedError

    @Command
    def VIEWNewCaption(self, caption:str) -> None:
        raise NotImplementedError

    @Command
    def VIEWNewBoard(self, xml_data:bytes) -> None:
        raise NotImplementedError

    @Command
    def VIEWSetInput(self, text:str) -> None:
        raise NotImplementedError

    @Command
    def VIEWSetMatches(self, str_list:List[str], selection:str=None) -> None:
        raise NotImplementedError

    @Command
    def VIEWSetMappings(self, str_list:List[str], selection:str=None) -> None:
        raise NotImplementedError

    @Command
    def VIEWSetLink(self, link_ref:str) -> None:
        raise NotImplementedError
