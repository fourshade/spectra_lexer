from .state import ViewState
from spectra_lexer.core import Command, Option
from spectra_lexer.resource import ConfigDictionary
from spectra_lexer.steno import LX

ConfigOption = Option()


class VIEW(LX):

    CONFIG_INFO: list = ConfigOption  # Keeps track of configuration options in a master dict.

    @Command
    def VIEWConfigUpdate(self, cfg:ConfigDictionary) -> None:
        """ Update all config values on existing components. """
        raise NotImplementedError

    @Command
    def VIEWDialogNoIndex(self) -> bool:
        """ Send this command if there is no index loaded on start. """
        raise NotImplementedError

    @Command
    def VIEWDialogMakeIndex(self, index_size:int) -> None:
        """ Make a normal index if <index_size> > 0, otherwise make an empty one. Save and send out the result. """
        raise NotImplementedError

    @Command
    def VIEWDialogFileLoad(self, filenames:list, res_type:str) -> None:
        """ Attempt to load resources from files chosen in a dialog. Print a status message if successful. """
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
        """ Do a value lookup after special checks. """
        raise NotImplementedError

    @Command
    def VIEWSelect(self, state:ViewState) -> None:
        """ Do a lexer query based on the current search selections. """
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
    def VIEWAction(self, action:str, state:ViewState) -> None:
        """ Perform any action above with the given state, then send it back. """
        raise NotImplementedError

    @Command
    def VIEWActionResult(self, state:ViewState) -> None:
        """ Send this command with the changed state as a result of any action. """
        raise NotImplementedError
