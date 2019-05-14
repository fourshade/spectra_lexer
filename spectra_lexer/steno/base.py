from typing import Callable, Iterable, List, Tuple

from .graph import StenoGraph
from spectra_lexer.core import Command
from spectra_lexer.resource import RS, RulesDictionary, StenoIndex, StenoRule
from spectra_lexer.system import ConsoleCommand


class LX(RS):

    @ConsoleCommand
    def LXLexerQuery(self, keys:str, word:str, *, need_all_keys:bool=False) -> StenoRule:
        """ Return and send out the best rule that maps the given key string to the given word. """
        raise NotImplementedError

    @ConsoleCommand
    def LXLexerQueryProduct(self, keys:Iterable[str], words:Iterable[str], *, need_all_keys:bool=False) -> StenoRule:
        """ As arguments, take iterables of keys and words and test every possible pairing.
            Return and send out the best rule out of all combinations. """
        raise NotImplementedError

    @ConsoleCommand
    def LXQueryAll(self, filter_in:Callable=None, filter_out:Callable=None, **kwargs) -> List[StenoRule]:
        """ Run the lexer in parallel on all currently loaded translations and return a list of results.
            <filter_in> eliminates translations before processing, and <filter_out> eliminates results afterward. """
        raise NotImplementedError

    @ConsoleCommand
    def LXAnalyzerMakeRules(self, filter_in:Callable=None, filter_out:Callable=None, **kwargs) -> RulesDictionary:
        """ Run the lexer on all currently loaded translations and make a new rule dict with auto-generated names. """
        raise NotImplementedError

    @ConsoleCommand
    def LXAnalyzerMakeIndex(self, size:int) -> StenoIndex:
        """ Generate a set of rules from translations using the lexer and compare them to the built-in rules.
            Make a index for each built-in rule containing a dict of every translation that used it. """
        raise NotImplementedError

    @ConsoleCommand
    def LXSearchQuery(self, pattern:str, **kwargs) -> List[str]:
        """ Determine the correct dict and perform a general search with the given mode. """
        raise NotImplementedError

    @ConsoleCommand
    def LXSearchLookup(self, pattern:str, match:str, **kwargs) -> List[str]:
        """ Perform a normal dict lookup. We still require the original pattern to tell what dict it was. """
        raise NotImplementedError

    @Command
    def LXSearchFindLink(self, rule:StenoRule) -> str:
        """ Look for the given rule in the index. If there are examples, return the link reference. """
        raise NotImplementedError

    @Command
    def LXSearchExamples(self, link_name:str, **kwargs) -> Tuple[str, str]:
        """ If the link on the diagram is clicked, get a random translation using this rule and search near it. """
        raise NotImplementedError

    @ConsoleCommand
    def LXGraphGenerate(self, rule:StenoRule, recursive:bool=True, compressed:bool=True) -> StenoGraph:
        """ Generate text graph data (of either type) from an output rule based on parameter options. """
        raise NotImplementedError

    @ConsoleCommand
    def LXBoardFromKeys(self, keys:str, ratio:float=None) -> bytes:
        """ Generate board diagram layouts arranged in columns according to <ratio> from a set of steno keys. """
        raise NotImplementedError

    @ConsoleCommand
    def LXBoardFromRule(self, rule:StenoRule, ratio:float=None, *, show_compound:bool=True) -> bytes:
        """ Generate board diagram layouts arranged in columns according to <ratio> from a steno rule.
            If <show_compound> is True, special keys may be shown corresponding to certain named rules. """
        raise NotImplementedError
