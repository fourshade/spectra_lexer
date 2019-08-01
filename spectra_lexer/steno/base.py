from typing import Dict, Iterable, List, Tuple

from .graph import StenoGraph
from spectra_lexer.core import ConsoleCommand
from spectra_lexer.resource import StenoRule


class LX:

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
    def LXAnalyzerMakeRules(self, *args, **kwargs) -> List[StenoRule]:
        """ Make a new rules list by running the lexer in parallel on all currently loaded translations. """
        raise NotImplementedError

    @ConsoleCommand
    def LXAnalyzerMakeIndex(self, *args) -> Dict[str, dict]:
        """ Generate a set of rules from translations using the lexer and compare them to the built-in rules.
            Make a index for each built-in rule containing a dict of every translation that used it. """
        raise NotImplementedError

    @ConsoleCommand
    def LXGraphGenerate(self, rule:StenoRule, **kwargs) -> StenoGraph:
        """ Generate text graph data from a rule. """
        raise NotImplementedError

    @ConsoleCommand
    def LXBoardFromKeys(self, keys:str, *args) -> bytes:
        """ Generate encoded board diagram layouts arranged according to <aspect_ratio> from a set of steno keys. """
        raise NotImplementedError

    @ConsoleCommand
    def LXBoardFromRule(self, rule:StenoRule, *args) -> bytes:
        """ Generate encoded board diagram layouts arranged according to <aspect_ratio> from a steno rule. """
        raise NotImplementedError

    @ConsoleCommand
    def LXSearchQuery(self, pattern:str, match:str=None, **kwargs) -> List[str]:
        """ Choose an index to use based on delimiters in the input pattern.
            Search for matches in that index. If <match> is given, the search will find mappings instead. """
        raise NotImplementedError

    @ConsoleCommand
    def LXSearchFindExample(self, link:str, **kwargs) -> Tuple[str, str]:
        """ Find an example translation in the index for the given link and return it with the required input text. """
        raise NotImplementedError

    @ConsoleCommand
    def LXSearchFindLink(self, rule:StenoRule) -> str:
        """ Return the name of the given rule to use in a link, but only if it has examples in the index. """
        raise NotImplementedError

    @ConsoleCommand
    def LXSearchFindRule(self, link:str) -> StenoRule:
        """ Return the rule under the given link name, or None if there is no rule by that name. """
        raise NotImplementedError
