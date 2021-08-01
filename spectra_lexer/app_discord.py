from typing import Optional

from spectra_lexer import Spectra
from spectra_lexer.discord.image import SVGRasterizer
from spectra_lexer.discord.main import DiscordApplication, DiscordMessage
from spectra_lexer.resource.rules import StenoRule
from spectra_lexer.spc_board import BoardDiagram, BoardEngine
from spectra_lexer.spc_lexer import StenoAnalyzer
from spectra_lexer.spc_search import SearchEngine


class DiscordConsoleApplication(DiscordApplication):
    """ Spectra console application that accepts string input from Discord users. """

    FILLER_CHAR = "-"        # Filler to replace each character in a word with no matches.
    TR_DELIMS = ["→", "->"]  # Possible delimiters between strokes and text in a query. Captions use the first one.

    def __init__(self, search_engine:SearchEngine, analyzer:StenoAnalyzer,
                 board_engine:BoardEngine, rasterizer:SVGRasterizer, *,
                 find_phrases=True, split_trans:dict=None, query_max_chars:int=None, board_AR:float=None) -> None:
        self._search_engine = search_engine
        self._analyzer = analyzer
        self._board_engine = board_engine
        self._rasterizer = rasterizer
        self._find_phrases = find_phrases        # If True, attempt searches for multi-word phrases.
        self._split_trans = split_trans          # Optional str.translate dictionary for phrase splitting.
        self._query_max_chars = query_max_chars  # Optional limit for # of characters allowed in a user query string.
        self._board_AR = board_AR                # Optional fixed aspect ratio for board images.

    def _build_message(self, text:str, diagram:BoardDiagram=None) -> DiscordMessage:
        """ Generate a Discord message with some text and optionally a board diagram.
            Discord will not embed SVGs directly, so use PNG raster format. """
        msg = DiscordMessage(text)
        if diagram is not None:
            png_data = self._rasterizer.encode(diagram, "PNG")
            msg.attach_file(png_data, "board.png")
        return msg

    def _query_keys(self, query:str) -> Optional[StenoRule]:
        """ Parse a user query string as a steno stroke string. """
        if query.isupper() and len(query.split()) == 1:
            return self._analyzer.query(query, "")

    def _query_delimited(self, query:str) -> Optional[StenoRule]:
        """ Parse a user query string as delimited strokes and English text. """
        for delim in self.TR_DELIMS:
            if delim in query:
                keys, letters = query.split(delim, 1)
                return self._analyzer.query(keys.strip(), letters.strip())

    def _query_search(self, query:str) -> StenoRule:
        """ Replace special characters in <query> and split the result on whitespace.
            Do an advanced lookup and return an analysis using the best strokes paired with each fragment. """
        if self._split_trans is not None:
            query = query.translate(self._split_trans)
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
                word = self.FILLER_CHAR * len(word)
            else:
                keys = self._analyzer.best_translation(matches, word)
            translations += [(keys, word), delim]
        return self._analyzer.compound_query(translations[:-1])

    def _query(self, query:str) -> Optional[StenoRule]:
        """ Try parsing a user query string using several methods. """
        for method in (self._query_keys, self._query_delimited, self._query_search):
            analysis = method(query)
            if analysis is not None and analysis.keys:
                return analysis

    def run(self, text:str) -> Optional[DiscordMessage]:
        """ Parse a user query string and return a Discord bot message, possibly with a board PNG attached. """
        query = text.strip()
        if not query:
            return None
        if self._query_max_chars is not None and len(query) > self._query_max_chars:
            return self._build_message('Query is too long.')
        analysis = self._query(query)
        if analysis is None:
            return self._build_message('Analysis failed.')
        keys = analysis.keys
        letters = analysis.letters
        if letters:
            show_letters = not query.startswith('+')
            caption = f'{keys} {self.TR_DELIMS[0]} {letters}'
            board_data = self._board_engine.draw_rule(analysis, aspect_ratio=self._board_AR, show_letters=show_letters)
        else:
            caption = keys
            board_data = self._board_engine.draw_keys(keys, aspect_ratio=self._board_AR)
        return self._build_message(f"`{caption}`", board_data)


def build_app(spectra:Spectra) -> DiscordApplication:
    io = spectra.resource_io
    analyzer = spectra.analyzer
    board_engine = spectra.board_engine
    rasterizer = SVGRasterizer(400, 300)
    translations = io.load_json_translations(*spectra.translations_paths)
    # Ignore Plover glue and case metacharacters so our search engine has a chance to find the actual text.
    search_engine = SearchEngine(' ', ' {<&>}')
    search_engine.set_translations(translations)
    split_trans = {ord(c): ' ' for c in r'''#$%&()*+-,.?!/:;<=>@[\]^_`"{|}~'''}
    return DiscordConsoleApplication(search_engine, analyzer, board_engine, rasterizer,
                                     split_trans=split_trans, query_max_chars=100, board_AR=400/300)
