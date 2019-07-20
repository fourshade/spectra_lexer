from typing import Callable, Iterable, Optional, Tuple

from spectra_lexer.resource import RS, RulesDictionary, StenoIndex, StenoRule
from spectra_lexer.system import ConsoleCommand


class LX(RS):

    @ConsoleCommand
    def LXLexerQuery(self, keys:str, word:str, **kwargs) -> StenoRule:
        """ Return and send out the best rule that maps the given key string to the given word. """
        raise NotImplementedError

    @ConsoleCommand
    def LXLexerQueryProduct(self, keys:Iterable[str], words:Iterable[str], **kwargs) -> StenoRule:
        """ As arguments, take iterables of keys and words and test every possible pairing.
            Return and send out the best rule out of all combinations. """
        raise NotImplementedError

    @ConsoleCommand
    def LXLexerQueryAll(self, filter_in:Callable=None, filter_out:Callable=None, **kwargs) -> RulesDictionary:
        """ Run the lexer in parallel on all currently loaded translations.
            Make a new rule dict with auto-generated names, using the built-in rules for dereferencing on encode.
            <filter_in> eliminates translations before processing, and <filter_out> eliminates results afterward. """
        raise NotImplementedError

    @ConsoleCommand
    def LXLexerMakeIndex(self, *args) -> StenoIndex:
        """ Generate a set of rules from translations using the lexer and compare them to the built-in rules.
            Make a index for each built-in rule containing a dict of every translation that used it. """
        raise NotImplementedError

    @ConsoleCommand
    def LXGraphGenerate(self, rule:StenoRule, *, recursive:bool=True, compressed:bool=True,
                        ref:str="", prev:StenoRule=None, select:bool=False) -> Tuple[str, Optional[StenoRule]]:
        """ Generate text graph data and selections from a rule. """
        raise NotImplementedError

    @ConsoleCommand
    def LXBoardFromKeys(self, keys:str, aspect_ratio:float=None) -> bytes:
        """ Generate encoded board diagram layouts arranged according to <aspect_ratio> from a set of steno keys. """
        raise NotImplementedError

    @ConsoleCommand
    def LXBoardFromRule(self, rule:StenoRule, aspect_ratio:float=None) -> bytes:
        """ Generate encoded board diagram layouts arranged according to <aspect_ratio> from a steno rule. """
        raise NotImplementedError
