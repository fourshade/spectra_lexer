from collections import defaultdict
from typing import Dict, Iterable, List

from .board import BoardEngine
from .filter import TranslationSizeFilter
from .graph import GraphEngine
from .keys import KeyLayout
from .lexer import LexerResult, StenoLexer
from .parallel import ParallelMapper
from .search import ExampleSearchEngine, SearchResults, TranslationSearchEngine

_RAW_RULES_TP = Dict[str, list]
_TR_DICT_TP = Dict[str, str]


class StenoAnalysisPage:

    def __init__(self, graph:str, caption:str, board:bytes, rule_id="") -> None:
        self.graph = graph      # HTML text graph for this selection.
        self.caption = caption  # Caption to go above the board diagram.
        self.board = board      # XML document containing SVG board diagram.
        self.rule_id = rule_id  # If the selection uses a rule, its rule ID, else an empty string.


class StenoAnalysis:

    def __init__(self, keys:str, letters:str, pages:Dict[str, StenoAnalysisPage], default:StenoAnalysisPage) -> None:
        self.keys = keys             # Translation keys in RTFCRE.
        self.letters = letters       # Translation letters.
        self.pages_by_ref = pages    # Analysis pages keyed by HTML anchor reference.
        self.default_page = default  # Default starting analysis page. May also be included in pages_by_ref.


class StenoEngine:
    """ Main access point for steno analysis. Generates rules from translations and creates visual representations. """

    def __init__(self, layout:KeyLayout, lexer:StenoLexer,
                 board_engine:BoardEngine, graph_engine:GraphEngine, captions:Dict[str, str]) -> None:
        self._layout = layout  # Converts between user RTFCRE steno strings and s-keys.
        self._lexer = lexer
        self._board_engine = board_engine
        self._graph_engine = graph_engine
        self._captions = captions
        self._translations = TranslationSearchEngine()
        self._examples = ExampleSearchEngine()

    def set_translations(self, translations:Dict[str, str]) -> None:
        """ Create a new translations search engine. """
        self._translations = TranslationSearchEngine(translations)

    def set_index(self, index:Dict[str, dict]) -> None:
        """ Create a new example search engine. """
        self._examples = ExampleSearchEngine(index)

    def search_translations(self, pattern:str, **kwargs) -> SearchResults:
        """ Do a new translations search.
            count   - Maximum number of matches returned.
            strokes - If True, search for strokes instead of translations.
            regex   - If True, treat the search pattern as a regular expression. """
        return self._translations.search(pattern, **kwargs)

    def search_examples(self, link_ref:str, pattern="", **kwargs) -> SearchResults:
        """ Search for examples of the named rule (if there are examples in the index).
            count   - Maximum number of matches returned.
            strokes - If True, search for strokes instead of translations. """
        return self._examples.search(link_ref, pattern, **kwargs)

    def lexer_query(self, keys:str, letters:str, **kwargs) -> LexerResult:
        """ Return the best rule matching <keys> to <letters>. Thoroughly parse the key string into s-keys first. """
        skeys = self._layout.from_rtfcre(keys)
        return self._lexer.query(skeys, letters, **kwargs)

    def lexer_best_strokes(self, keys_iter:Iterable[str], letters:str) -> str:
        """ Return the best (most accurate) set of strokes from <keys_iter> that matches <letters>.
            Prefer shorter strokes over longer ones on ties. """
        keys_list = sorted(keys_iter, key=len)
        tr_list = [(self._layout.from_rtfcre(keys), letters) for keys in keys_list]
        best_index = self._lexer.find_best_translation(tr_list)
        return keys_list[best_index]

    def analyze(self, keys:str, letters:str, *, match_all_keys:bool, select_ref:str, find_rule:bool,
                graph_compress:bool, graph_compat:bool, graph_intense:bool,
                board_ratio:float, board_compound:bool) -> StenoAnalysisPage:
        """ Run a lexer query and return an analysis page to update the user GUI state. """
        result = self.lexer_query(keys, letters, match_all_keys=match_all_keys)
        unmatched_skeys = result.unmatched_skeys()
        names = result.rules()
        positions = result.rule_positions()
        lengths = result.rule_lengths()
        connections = list(zip(names, positions, lengths))
        # Convert unmatched keys back to RTFCRE format for the graph and caption.
        unmatched_keys = self._layout.to_rtfcre(unmatched_skeys)
        root = self._graph_engine.make_tree(letters, connections, unmatched_keys)
        target = None
        for node in root:
            ref = node.rule() if find_rule else node.ref()
            if ref == select_ref:
                target = node
                break
        text = root.render(target, compressed=graph_compress, compat=graph_compat, intense=graph_intense)
        # If nothing is selected, generate the board and caption for the root node.
        if target is None:
            target = root
        rule_name: str = target.rule()
        if target is root:
            caption = result.caption()
            names = result.rules()
        elif rule_name == self._graph_engine.NAME_UNMATCHED:
            caption = unmatched_keys + ": unmatched keys"
            names = []
        else:
            caption = self._captions[rule_name]
            names = [rule_name]
            unmatched_skeys = ""
        xml = self._board_engine.from_rules(names, unmatched_skeys, board_ratio, compound=board_compound)
        link_ref = rule_name if rule_name in self._examples else ""
        return StenoAnalysisPage(text, caption, xml, link_ref)

    def make_index(self, *args, **kwargs) -> Dict[str, _TR_DICT_TP]:
        """ Run the lexer on all <translations> with an input filter and look at the top-level rule names.
            Make a index containing a dict for each built-in rule with every translation that used it. """
        translations = self._translations.to_dict()
        return _IndexFactory(self._layout, self._lexer).make_index(translations, *args, **kwargs)


class _IndexFactory:
    """ Factory for an examples index using multiprocessing with the lexer. """

    def __init__(self, layout:KeyLayout, lexer:StenoLexer) -> None:
        self._layout = layout  # Converts between user RTFCRE steno strings and s-keys.
        self._lexer = lexer

    def make_index(self, translations, *args, **kwargs) -> Dict[str, _TR_DICT_TP]:
        """ Run the lexer on all <translations> with an input filter and look at the top-level rule names.
            Make a index containing a dict for each built-in rule with every translation that used it. """
        tr_filter = TranslationSizeFilter(*args)
        translations = tr_filter.filter(translations)
        mapper = ParallelMapper(self._query, **kwargs)
        index = defaultdict(dict)
        for keys, letters, *names in mapper.starmap(translations.items()):
            for name in names:
                index[name][keys] = letters
        return index

    def _query(self, keys:str, letters:str) -> List[str]:
        """ Make a lexer query and return the rule names in a list with its matching keys and letters.
            This is required for parallel operations where results may be returned out of order. """
        skeys = self._layout.from_rtfcre(keys)
        result = self._lexer.query(skeys, letters)
        data = [keys, letters]
        # Only fully matched translations should have rules recorded in the index.
        if not result.unmatched_skeys():
            data += result.rules()
        return data
