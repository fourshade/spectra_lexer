from typing import Dict, Sequence, Tuple

from .board import BoardEngine
from .caption import BoardCaptioner
from .graph import GraphEngine
from .index import IndexFactory
from .keys import KeyLayout
from .lexer import LexerResult, StenoLexer
from .search import ExamplesDict, ExampleSearchEngine, SearchResults, TranslationsDict, TranslationSearchEngine

_TRANSLATION = Tuple[str, str]  # Translation with keys in RTFCRE.


class StenoAnalysisPage:
    """ Data class that contains an HTML formatted graph, a caption, and an SVG board. """

    def __init__(self, graph:str, intense_graph:str, caption:str, board:bytes, rule_id="") -> None:
        self.graph = graph                  # HTML text graph for this selection.
        self.intense_graph = intense_graph  # Brighter HTML text graph for this selection.
        self.caption = caption              # Caption to go above the board diagram.
        self.board = board                  # XML document containing SVG board diagram.
        self.rule_id = rule_id              # If the selection uses a rule, its rule ID, else an empty string.


class StenoAnalysis:
    """ Data class that contains graphical data for an entire analysis. """

    def __init__(self, keys:str, letters:str, pages:Dict[str, StenoAnalysisPage], default:StenoAnalysisPage) -> None:
        self.keys = keys             # Translation keys in RTFCRE.
        self.letters = letters       # Translation letters.
        self.pages_by_ref = pages    # Analysis pages keyed by HTML anchor reference.
        self.default_page = default  # Default starting analysis page. May also be included in pages_by_ref.


class StenoGUIOutput:
    """ Data class that contains an entire GUI update. All fields are optional. """

    def __init__(self, search_input:str=None, search_results:SearchResults=None, analysis:StenoAnalysis=None) -> None:
        self.search_input = search_input      # Product of an example search action.
        self.search_results = search_results  # Product of a search action.
        self.analysis = analysis              # Product of a query action.


class StenoEngine:
    """ Main access point for steno analysis. Generates rules from translations and creates visual representations. """

    def __init__(self, layout:KeyLayout, lexer:StenoLexer,
                 board_engine:BoardEngine, graph_engine:GraphEngine, captioner:BoardCaptioner) -> None:
        self._layout = layout  # Converts between user RTFCRE steno strings and s-keys.
        self._lexer = lexer
        self._board_engine = board_engine
        self._graph_engine = graph_engine
        self._captioner = captioner
        self._translations = TranslationSearchEngine()
        self._examples = ExampleSearchEngine()

    def set_translations(self, translations:TranslationsDict) -> None:
        """ Create a new translations search engine. """
        self._translations = TranslationSearchEngine(translations)

    def set_index(self, index:ExamplesDict) -> None:
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

    def lexer_best_translation(self, translations:Sequence[_TRANSLATION]) -> _TRANSLATION:
        """ Return the best (most accurate) from a sequence of <translations>. """
        assert translations
        if len(translations) == 1:
            return translations[0]
        converted = [(self._layout.from_rtfcre(keys), letters) for keys, letters in translations]
        best_index = self._lexer.find_best_translation(converted)
        return translations[best_index]

    def make_index(self, *args, **kwargs) -> ExamplesDict:
        """ Run the lexer on all <translations> with an input filter and look at the top-level rule names.
            Make a index containing a dict for each built-in rule with every translation that used it. """
        translations = self._translations.to_dict()
        return IndexFactory(self._layout, self._lexer).make_index(translations, *args, **kwargs)

    def analyze(self, keys:str, letters:str, result:LexerResult,
                graph_compress:bool, graph_compat:bool, board_ratio:float, board_compound:bool) -> StenoAnalysis:
        """ Return a full analysis of a lexer query for the GUI. """
        names = result.rule_ids()
        positions = result.rule_positions()
        unmatched_skeys = result.unmatched_skeys()
        # Convert unmatched keys back to RTFCRE format for the graph and caption.
        unmatched_keys = self._layout.to_rtfcre(unmatched_skeys)
        root = self._graph_engine.make_tree(letters, names, positions, unmatched_keys)
        pages = {}
        for target in root:
            link_ref = ""
            board_names = target.rule_ids()
            board_unmatched = ""
            if target is root:
                caption = self._captioner.result_caption(result)
                board_unmatched = unmatched_skeys
            elif board_names:
                name = board_names[0]
                caption = self._captioner.rule_caption(name)
                if name in self._examples:
                    link_ref = name
            else:
                caption = self._captioner.unmatched_caption(unmatched_keys)
                board_unmatched = unmatched_skeys
            texts = [root.render(target, compressed=graph_compress, compat=graph_compat, intense=intense)
                     for intense in (False, True)]
            xml = self._board_engine.from_rules(board_names, board_unmatched, board_ratio, compound=board_compound)
            pages[target.ref()] = StenoAnalysisPage(*texts, caption, xml, link_ref)
        # If nothing is selected, use the board and caption for the root node.
        root_page = pages[root.ref()]
        default_text = root.render(None, compressed=graph_compress, compat=graph_compat)
        default_page = StenoAnalysisPage(default_text, default_text, root_page.caption, root_page.board, "")
        return StenoAnalysis(keys, letters, pages, default_page)

    class _SearchOptions:
        """ Input option values for search actions. """
        search_mode_strokes: bool = False       # If True, search for strokes instead of translations.
        search_mode_regex: bool = False         # If True, perform search using regex characters.
        search_match_limit: int = 100           # Maximum number of matches returned on one page of a search.

    class _AnalysisOptions:
        """ Input option values for analysis actions. """
        lexer_strict_mode: bool = False         # Only return lexer results that match every key in a translation.
        board_aspect_ratio: float = 100.0       # Aspect ratio for board viewing area.
        board_compound_key_labels: bool = True  # Show special labels for compound keys (i.e. `f` instead of TP).
        graph_compressed_layout: bool = True    # Compress the graph layout vertically to save space.
        graph_compatibility_mode: bool = False  # Force correct spacing in the graph using HTML tables.

    class _EngineOptions(_SearchOptions, _AnalysisOptions):
        def __init__(self, state_dict:dict) -> None:
            """ Update state attributes directly. """
            self.__dict__.update(state_dict)

    _INDEX_DELIM = ";"  # Delimiter between rule name and query for example index searches.

    def process_action(self, action:str, *args, **options) -> StenoGUIOutput:
        """ Entry point to the GUI state machine. Perform a GUI action and return the changes. """
        opts = self._EngineOptions(options)
        method = getattr(self, "RUN" + action)
        return method(*args, options=opts)

    def RUNSearchExamples(self, link_ref:str, *, options:_EngineOptions) -> StenoGUIOutput:
        """ When a link is clicked, search for examples of the named rule and select one. """
        keys, letters = self._examples.random_translation(link_ref)
        if not keys or not letters:
            return StenoGUIOutput()
        pattern = keys if options.search_mode_strokes else letters
        new_input = link_ref + self._INDEX_DELIM + pattern
        return StenoGUIOutput(search_input=new_input,
                              search_results=self._call_search(new_input, 1, options),
                              analysis=self._exec_query(keys, letters, options))

    def RUNSearch(self, pattern:str, pages=1, *, options:_SearchOptions) -> StenoGUIOutput:
        """ Do a new search. """
        return StenoGUIOutput(search_results=self._call_search(pattern, pages, options))

    def _call_search(self, pattern:str, pages:int, options:_SearchOptions) -> SearchResults:
        """ Do a new search and return results unless the input is blank. """
        if not pattern:
            return SearchResults()
        kwargs = dict(count=pages * options.search_match_limit, strokes=options.search_mode_strokes)
        if self._INDEX_DELIM in pattern:
            args = pattern.split(self._INDEX_DELIM, 1)
            return self.search_examples(*args, **kwargs)
        else:
            return self.search_translations(pattern, regex=options.search_mode_regex, **kwargs)

    def RUNQuery(self, *translations:_TRANSLATION, options:_AnalysisOptions) -> StenoGUIOutput:
        """ Execute and display a graph of a lexer query from search results or user strokes. """
        keys, letters = self.lexer_best_translation(translations)
        if not keys or not letters:
            return StenoGUIOutput()
        return StenoGUIOutput(analysis=self._exec_query(keys, letters, options))

    def _exec_query(self, keys:str, letters:str, options:_AnalysisOptions) -> StenoAnalysis:
        """ Execute a new lexer query and analysis and return the output with graphs and boards. """
        result = self.lexer_query(keys, letters, match_all_keys=options.lexer_strict_mode)
        return self.analyze(keys, letters, result,
                            graph_compress=options.graph_compressed_layout,
                            graph_compat=options.graph_compatibility_mode,
                            board_ratio=options.board_aspect_ratio,
                            board_compound=options.board_compound_key_labels)
