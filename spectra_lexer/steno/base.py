from typing import Dict, Iterable, List, Tuple

from .graph import StenoGraph
from .resource import StenoRule


class LX:

    def LXLexerQuery(self, keys:str, word:str, **kwargs) -> StenoRule:
        raise NotImplementedError

    def LXLexerQueryProduct(self, keys:Iterable[str], words:Iterable[str], **kwargs) -> StenoRule:
        raise NotImplementedError

    def LXAnalyzerMakeRules(self, *args, **kwargs) -> List[StenoRule]:
        raise NotImplementedError

    def LXAnalyzerMakeIndex(self, *args) -> Dict[str, dict]:
        raise NotImplementedError

    def LXGraphGenerate(self, rule:StenoRule, **kwargs) -> StenoGraph:
        raise NotImplementedError

    def LXBoardFromKeys(self, keys:str, *args) -> bytes:
        raise NotImplementedError

    def LXBoardFromRule(self, rule:StenoRule, *args) -> bytes:
        raise NotImplementedError

    def LXSearchQuery(self, pattern:str, match:str=None, **kwargs) -> List[str]:
        raise NotImplementedError

    def LXSearchFindExample(self, link:str, **kwargs) -> Tuple[str, str]:
        raise NotImplementedError

    def LXSearchFindLink(self, rule:StenoRule) -> str:
        raise NotImplementedError

    def LXSearchFindRule(self, link:str) -> StenoRule:
        raise NotImplementedError
