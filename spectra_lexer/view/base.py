from typing import List

from .config import ConfigItem
from spectra_lexer.core import Command
from spectra_lexer.steno import LX


class VIEW(LX):

    @Command
    def VIEWConfigInfo(self, info:List[ConfigItem]) -> None:
        """ Send this command with formatted config info from active components. """
        raise NotImplementedError

    @Command
    def VIEWConfigUpdate(self, options:dict) -> None:
        """ Update and save all config options to disk. """
        raise NotImplementedError

    @Command
    def VIEWDialogIndexDone(self) -> None:
        """ Send this command when an index creation finishes. """
        raise NotImplementedError

    @Command
    def VIEWDialogNoIndex(self) -> bool:
        """ Send this command if there is no index loaded on start. """
        raise NotImplementedError

    @Command
    def VIEWDialogMakeIndex(self, index_size:int) -> None:
        """ Make an index, save it, and send out the result. """
        raise NotImplementedError

    @Command
    def VIEWDialogSkipIndex(self) -> None:
        """ Make an empty index and save it. """
        raise NotImplementedError

    @Command
    def VIEWDialogIndexDone(self) -> None:
        """ Send this command when an index creation finishes. """
        raise NotImplementedError

    @Command
    def VIEWDialogFileLoad(self, filenames:List[str], res_type:str) -> None:
        """ Attempt to load resources from files chosen in a dialog. Print a status message if successful. """
        raise NotImplementedError

    @Command
    def VIEWAction(self, state:dict, action:str="") -> None:
        """ Perform any action above with the given state dict, then send it back with the changes. """
        raise NotImplementedError

    @Command
    def VIEWActionResult(self, changed:dict) -> None:
        """ Send this command with the state changes as a result of any action. """
        raise NotImplementedError
