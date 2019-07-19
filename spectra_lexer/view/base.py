from spectra_lexer.core import Command, OptionGroup, Resource
from spectra_lexer.steno import LX
from spectra_lexer.types.codec import CFGDict

ConfigDictionary = CFGDict
ConfigOption = OptionGroup()


class VIEW(LX):

    CONFIG: ConfigDictionary = Resource(ConfigDictionary())
    CONFIG_INFO: list = ConfigOption  # Keeps track of configuration options in a master dict.

    @Command
    def VIEWConfigLoad(self, *patterns:str, **kwargs) -> ConfigDictionary:
        """ Load and update all config options from disk. Ignore missing files. """
        raise NotImplementedError

    @Command
    def VIEWConfigSave(self, cfg:ConfigDictionary, filename:str="", **kwargs) -> None:
        """ Update and save all config options to disk. If no save filename is given, use the default. """
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
    def VIEWDialogIndexDone(self) -> None:
        """ Send this command when an index creation finishes. """
        raise NotImplementedError

    @Command
    def VIEWDialogFileLoad(self, filenames:list, res_type:str) -> None:
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
