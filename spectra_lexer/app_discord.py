from types import SimpleNamespace
from typing import Iterator, Optional, Sequence

from spectra_lexer import Spectra
from spectra_lexer.qt.svg import SVGRasterizer
from spectra_lexer.resource.rules import StenoRule
from spectra_lexer.spc_board import BoardDiagram, BoardEngine
from spectra_lexer.spc_lexer import StenoAnalyzer
from spectra_lexer.spc_search import SearchEngine

FILLER_CHAR = "-"        # Filler to replace each character in a word with no matches.
TR_DELIMS = ["→", "->"]  # Possible delimiters between strokes and text in a query. Captions must use one of these.
SPLIT_CHARS = r'''#$%&()*+-,.?!/:;<=>@[\]^_`"{|}~'''  # Characters to replace with spaces before phrase splitting.
SPLIT_TRANS = {ord(c): ' ' for c in SPLIT_CHARS}      # str.translate dictionary for phrase splitting.


class QueryPage(SimpleNamespace):
    """ Namespace for a page of query information usable in a Discord message. """

    title: str          # Page title (the diagram type).
    description: str    # Page description (the diagram caption).
    png_diagram: bytes  # Raw PNG data for board diagram.


QueryResult = Sequence[QueryPage]  # Full Discord query result.


class QueryError(ValueError):
    """ Raised with an error message if analysis was unsuccessful. """


class DiscordApplication:
    """ Spectra console application that accepts string input from Discord users. """

    def __init__(self, search_engine:SearchEngine, analyzer:StenoAnalyzer, board_engine:BoardEngine,
                 rasterizer:SVGRasterizer, *, find_phrases=True, max_chars:int=None, board_ratio:float=None) -> None:
        self._search_engine = search_engine
        self._analyzer = analyzer
        self._board_engine = board_engine
        self._rasterizer = rasterizer
        self._find_phrases = find_phrases  # If True, attempt searches for multi-word phrases.
        self._max_chars = max_chars        # Optional limit for # of characters allowed in a user query string.
        self._board_ratio = board_ratio    # Optional fixed aspect ratio for board images.

    def _query_keys(self, query:str) -> Optional[StenoRule]:
        """ Parse a user query string as a steno stroke string. """
        if query.isupper() and len(query.split()) == 1:
            return self._analyzer.query(query, "")

    def _query_delimited(self, query:str) -> Optional[StenoRule]:
        """ Parse a user query string as delimited strokes and English text. """
        for delim in TR_DELIMS:
            if delim in query:
                keys, letters = query.split(delim, 1)
                return self._analyzer.query(keys.strip(), letters.strip())

    def _query_search(self, query:str) -> StenoRule:
        """ Replace special characters in <query> and split the result on whitespace.
            Do an advanced lookup and return an analysis using the best strokes paired with each fragment. """
        query = query.translate(SPLIT_TRANS)
        stack = query.split()[::-1]
        delim = ("", ' ')
        translations = []
        while stack:
            word = stack.pop()
            matches = result = self._search_engine.lookup(word)
            while self._find_phrases and result and stack:
                phrase = word + ' ' + stack[-1]
                result = self._search_engine.lookup(phrase)
                if result:
                    matches = result
                    word = phrase
                    stack.pop()
            if not matches:
                keys = ""
                word = FILLER_CHAR * len(word)
            else:
                keys = self._analyzer.best_translation(matches, word)
            translations += [(keys, word), delim]
        return self._analyzer.compound_query(translations[:-1])

    def _draw_keys(self, keys:str) -> BoardDiagram:
        return self._board_engine.draw_keys(keys, aspect_ratio=self._board_ratio)

    def _draw_rule(self, analysis:StenoRule, *, show_letters=True) -> BoardDiagram:
        return self._board_engine.draw_rule(analysis, aspect_ratio=self._board_ratio, show_letters=show_letters)

    def _build_page(self, title:str, caption:str, diagram:BoardDiagram) -> QueryPage:
        """ Discord will not embed SVGs directly, so convert diagrams to PNG raster format. """
        png_diagram = self._rasterizer.encode(diagram, "PNG")
        return QueryPage(title=title, description=caption, png_diagram=png_diagram)

    def _iter_pages(self, analysis:StenoRule) -> Iterator[QueryPage]:
        """ Yield relevant analysis pages with board diagrams. """
        keys = analysis.keys
        key_diagram = self._draw_keys(keys)
        yield self._build_page('Key Diagram', keys, key_diagram)
        letters = analysis.letters
        if letters:
            caption = f'{keys} {TR_DELIMS[0]} {letters}'
            sounds_diagram = self._draw_rule(analysis, show_letters=False)
            yield self._build_page('Sounds Diagram', caption, sounds_diagram)
            text_diagram = self._draw_rule(analysis, show_letters=True)
            yield self._build_page('Text Diagram', caption, text_diagram)

    def run(self, text:str) -> QueryResult:
        """ Parse a user query string and return pages with analysis results if possible. """
        query = text.strip()
        if not query:
            raise QueryError('Query is empty.')
        if self._max_chars is not None and len(query) > self._max_chars:
            raise QueryError('Query is too long.')
        for method in (self._query_keys, self._query_delimited, self._query_search):
            analysis = method(query)
            if analysis is not None and analysis.keys:
                return list(self._iter_pages(analysis))
        raise QueryError('Analysis failed.')


def build_app(spectra:Spectra, max_width:int, max_height:int, *, max_chars=None) -> DiscordApplication:
    io = spectra.resource_io
    analyzer = spectra.analyzer
    board_engine = spectra.board_engine
    rasterizer = SVGRasterizer(max_width, max_height)
    translations = io.load_json_translations(*spectra.translations_paths)
    # Ignore Plover glue and case metacharacters so our search engine has a chance to find the actual text.
    search_engine = SearchEngine(' ', ' {<&>}')
    search_engine.set_translations(translations)
    return DiscordApplication(search_engine, analyzer, board_engine, rasterizer,
                              max_chars=max_chars, board_ratio=max_width/max_height)
