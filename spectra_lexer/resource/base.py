from .codec import CFGDict
from .index import StenoIndex
from .rules import RulesDictionary
from .translations import TranslationsDictionary
from spectra_lexer.core import Command, ConsoleCommand


class RS:

    @ConsoleCommand
    def RSSystemLoad(self, base_dir:str) -> dict:
        """ Load resources from a steno system directory. Use default settings if missing. """
        raise NotImplementedError

    @Command
    def RSSystemReady(self, **kwargs) -> None:
        """ Send this command with all system resources as keywords. """
        raise NotImplementedError

    @ConsoleCommand
    def RSTranslationsLoad(self, *patterns:str, **kwargs) -> TranslationsDictionary:
        """ Load and merge translations from disk. Ignore missing files. """
        raise NotImplementedError

    @Command
    def RSTranslationsReady(self, translations:TranslationsDictionary) -> None:
        """ Send this command with the new translations dict for all components. """
        raise NotImplementedError

    @ConsoleCommand
    def RSIndexLoad(self, *patterns:str, **kwargs) -> StenoIndex:
        """ Load an index from disk. Ignore missing files. """
        raise NotImplementedError

    @Command
    def RSIndexReady(self, index:StenoIndex) -> None:
        """ Send this command with the new index dict for all components. """
        raise NotImplementedError

    @ConsoleCommand
    def RSConfigLoad(self, *patterns:str, **kwargs) -> CFGDict:
        """ Load config settings from disk. Ignore missing files. """
        raise NotImplementedError

    @Command
    def RSConfigReady(self, cfg:CFGDict) -> None:
        """ Send this command with the new config dict for all components. """
        raise NotImplementedError

    @ConsoleCommand
    def RSRulesSave(self, rules:RulesDictionary, filename:str= "", **kwargs) -> None:
        """ Parse a rules dictionary back into raw form and save it to JSON. """
        raise NotImplementedError

    @ConsoleCommand
    def RSTranslationsSave(self, translations:TranslationsDictionary, filename:str= "", **kwargs) -> None:
        """ Save a translations dict directly into JSON. """
        raise NotImplementedError

    @ConsoleCommand
    def RSIndexSave(self, index:StenoIndex, filename:str= "", **kwargs) -> None:
        """ Save an index structure directly into JSON. Sort all rules and translations by key and set them active.
            Saving should not fail silently, unlike loading. If no save filename is given, use the default. """
        raise NotImplementedError

    @ConsoleCommand
    def RSConfigSave(self, cfg:CFGDict, filename:str="", **kwargs) -> None:
        """ Save a config dict into .cfg format. """
        raise NotImplementedError
