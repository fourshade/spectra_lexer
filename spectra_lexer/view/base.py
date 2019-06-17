from .state import ViewState
from spectra_lexer.core import Command, Option
from spectra_lexer.resource import ConfigDictionary
from spectra_lexer.steno import LX

ConfigOption = Option()


class VIEW(LX):

    CONFIG_INFO: Option = ConfigOption  # Keeps track of configuration options in a master dict.

    @Command
    def VIEWConfigUpdate(self, cfg:ConfigDictionary) -> None:
        """ Update all config values on existing components. """
        raise NotImplementedError

    @Command
    def VIEWSearchExamples(self, state:ViewState) -> None:
        """ When a link is clicked, search for examples of the named rule and select one. """
        raise NotImplementedError

    @Command
    def VIEWSearch(self, state:ViewState) -> None:
        """ Do a new search unless the input is blank. """
        raise NotImplementedError

    @Command
    def VIEWLookup(self, state:ViewState) -> None:
        """ Do a lookup after special checks. """
        raise NotImplementedError

    @Command
    def VIEWQuery(self, state:ViewState) -> None:
        """ Execute and display a lexer query. """
        raise NotImplementedError

    @Command
    def VIEWGraphOver(self, state:ViewState) -> None:
        """ On mouseover, highlight the node at (row, col) temporarily if nothing is selected. """
        raise NotImplementedError

    @Command
    def VIEWGraphClick(self, state:ViewState) -> None:
        """ On click, find the node owning the character at (row, col) and select it with a bright color. """
        raise NotImplementedError

    @Command
    def VIEWAction(self, state:ViewState) -> ViewState:
        """ Perform any action above with the given state, then return it with the changes. """
        raise NotImplementedError


class ViewConfig(VIEW):

    def Load(self) -> None:
        self.VIEWConfigUpdate(self.CONFIG)

    def VIEWConfigUpdate(self, cfg:ConfigDictionary) -> None:
        self.CONFIG_INFO = [(sect, name, val) for sect, page in cfg.items() for name, val in page.items()]
