from .index import StenoIndex
from .keys import KeyLayout
from .rules import RulesDictionary
from .translations import TranslationsDictionary
from spectra_lexer.core import Resource
from spectra_lexer.system import ConsoleCommand, SYS
from spectra_lexer.types.codec import CFGDict, XMLElement

BoardElementTree = XMLElement
ConfigDictionary = CFGDict


class RS(SYS):

    LAYOUT: KeyLayout = Resource()
    BOARD: BoardElementTree = Resource()
    RULES: RulesDictionary = Resource()
    TRANSLATIONS: TranslationsDictionary = Resource(TranslationsDictionary())
    INDEX: StenoIndex = Resource(StenoIndex())
    CONFIG: ConfigDictionary = Resource(ConfigDictionary())

    @ConsoleCommand
    def RSSystemLoad(self, base_dir:str) -> dict:
        """ Load resources from a steno system directory. Use default settings if missing. """
        raise NotImplementedError

    @ConsoleCommand
    def RSTranslationsLoad(self, *patterns:str, **kwargs) -> TranslationsDictionary:
        """ Load and merge translations from disk. Ignore missing files. """
        raise NotImplementedError

    @ConsoleCommand
    def RSIndexLoad(self, filename:str= "", **kwargs) -> StenoIndex:
        """ Load an index from disk. Ignore missing files. """
        raise NotImplementedError

    @ConsoleCommand
    def RSConfigLoad(self, *patterns:str, **kwargs) -> ConfigDictionary:
        """ Load all config options from disk. Ignore missing files. """
        raise NotImplementedError

    @ConsoleCommand
    def RSRulesSave(self, rules:RulesDictionary, filename:str= "", **kwargs) -> None:
        """ Parse a rules dictionary back into raw form and save it to JSON. """
        raise NotImplementedError

    @ConsoleCommand
    def RSTranslationsSave(self, d:TranslationsDictionary, filename:str= "", **kwargs) -> None:
        """ Save a translations dict directly into JSON. """
        raise NotImplementedError

    @ConsoleCommand
    def RSIndexSave(self, index:StenoIndex, filename:str= "", **kwargs) -> None:
        """ Save an index structure directly into JSON. Sort all rules and translations by key and set them active.
            Saving should not fail silently, unlike loading. If no save filename is given, use the default. """
        raise NotImplementedError

    @ConsoleCommand
    def RSConfigSave(self, cfg:ConfigDictionary, filename:str="", **kwargs) -> None:
        """ Update components and save all config options to disk. If no save filename is given, use the default. """
        raise NotImplementedError
