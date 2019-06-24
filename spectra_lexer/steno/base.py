from typing import Callable, Dict, Iterable, List, Optional, Tuple

from spectra_lexer.core import Command
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
    def LXLexerMakeIndex(self, size:int) -> StenoIndex:
        """ Generate a set of rules from translations using the lexer and compare them to the built-in rules.
            Make a index for each built-in rule containing a dict of every translation that used it. """
        raise NotImplementedError

    @ConsoleCommand
    def LXSearchQuery(self, pattern:str, **kwargs) -> List[str]:
        """ Determine the correct dict and perform a general search with the given mode. """
        raise NotImplementedError

    @Command
    def LXSearchFindLink(self, rule:StenoRule) -> str:
        """ Look for the given rule in the index. If there are examples, return the link reference. """
        raise NotImplementedError

    @Command
    def LXSearchExamples(self, link_name:str, **kwargs) -> str:
        """ If the link on the diagram is clicked, get a random translation using this rule. """
        raise NotImplementedError

    @ConsoleCommand
    def LXGraphGenerate(self, rule:StenoRule, *, recursive:bool=True, compressed:bool=True,
                        ref:str="", prev:StenoRule=None, select:bool=False) -> Tuple[str, Optional[StenoRule]]:
        """ Generate text graph data and selections from a rule. """
        raise NotImplementedError

    @ConsoleCommand
    def LXBoardFromKeys(self, keys:str, ratio:float=None) -> bytes:
        """ Generate board diagram layouts arranged in columns according to <ratio> from a set of steno keys. """
        raise NotImplementedError

    @ConsoleCommand
    def LXBoardFromRule(self, rule:StenoRule, ratio:float=None) -> bytes:
        """ Generate board diagram layouts arranged in columns according to <ratio> from a steno rule. """
        raise NotImplementedError
