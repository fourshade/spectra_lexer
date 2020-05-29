""" Main module for the Discord bot application. """

import sys
from typing import Optional

from spectra_lexer import SpectraOptions
from spectra_lexer.analysis import StenoAnalyzer, Translation
from spectra_lexer.discord import BotMessage, DiscordBot
from spectra_lexer.display import BoardEngine
from spectra_lexer.qt.svg import SVGConverter
from spectra_lexer.resource.rules import StenoRule
from spectra_lexer.search import MatchDict, SearchEngine


class DiscordApplication:
    """ Spectra engine application that accepts string input from Discord users. """

    def __init__(self, search_engine:SearchEngine, analyzer:StenoAnalyzer,
                 board_engine:BoardEngine, svg_converter:SVGConverter, *,
                 query_max_chars:int=None, query_trans:dict=None, search_depth=1, board_AR:float=None) -> None:
        self._search_engine = search_engine
        self._analyzer = analyzer
        self._board_engine = board_engine
        self._svg_converter = svg_converter      # Converter for SVG data to PNG (Discord will not embed SVGs.)
        self._query_max_chars = query_max_chars  # Optional limit for # of characters allowed in a user query string.
        self._query_trans = query_trans or {}    # Translation table to remove characters before searching for words.
        self._search_depth = search_depth        # Maximum number of search results to analyze at once.
        self._board_AR = board_AR                # Optional fixed aspect ratio for board images.

    def _best_translation(self, word:str, matches:MatchDict) -> Translation:
        """ Find the best pairing between a word and its possible stroke matches. """
        if not matches:
            return ("?", "-" * len(word))
        if word in matches:
            pairs = [(s, word) for s in matches[word]]
        elif word.lower() in matches:
            pairs = [(s, word) for s in matches[word.lower()]]
        else:
            pairs = [(s, match) for match, strokes_list in matches.items() for s in strokes_list]
        return self._analyzer.best_translation(pairs)

    def _analyze_words(self, query:str) -> Optional[StenoRule]:
        """ Do an advanced lookup to put together rules containing strokes for multiple words. """
        letters = query.translate(self._query_trans).strip()
        words = letters.split()
        search_list = [self._search_engine.search(word, self._search_depth) for word in words]
        if not any(search_list):
            return None
        translations = [self._best_translation(word + " ", matches) for word, matches in zip(words, search_list)]
        return self._analyzer.compound_query(translations)

    def _board_png(self, rule:StenoRule) -> bytes:
        """ Generate a board diagram in PNG raster format with good dimensions. """
        board = self._board_engine.draw_rule(rule, aspect_ratio=self._board_AR)
        svg_data = board.encode('utf-8')
        return self._svg_converter.to_png(svg_data)

    def exec(self, query:str) -> BotMessage:
        """ Parse a user query string and return a Discord bot message, possibly with a board PNG attached. """
        if self._query_max_chars is not None and len(query) > self._query_max_chars:
            return BotMessage('Query is too long.')
        analysis = self._analyze_words(query)
        if analysis is None:
            return BotMessage('No suggestions.')
        msg = BotMessage(f'``{analysis}``')
        png_data = self._board_png(analysis)
        msg.attach_as_file(png_data, "board.png")
        return msg


def main() -> int:
    opts = SpectraOptions("Run Spectra as a Discord bot.")
    opts.add("token", "", "Discord bot token (REQUIRED).")
    spectra = opts.compile()
    translations_files = opts.translations_paths()
    log = spectra.log
    io = spectra.translations_io
    search_engine = spectra.search_engine
    analyzer = spectra.analyzer
    board_engine = spectra.board_engine
    log("Loading...")
    translations = io.load_json_translations(*translations_files)
    search_engine.set_translations(translations)
    svg_converter = SVGConverter(background_rgba=(0, 0, 0, 0))
    excluded_chars = r'''#$%&()*+-,.?!/:;<=>@[\]^_`"{|}~'''
    map_to_space = dict.fromkeys(map(ord, excluded_chars), ' ')
    app = DiscordApplication(search_engine, analyzer, board_engine, svg_converter,
                             query_max_chars=100, query_trans=map_to_space, search_depth=3, board_AR=1.5)
    bot = DiscordBot(opts.token, log)
    bot.add_command("spectra", app.exec)
    return bot.run()


if __name__ == '__main__':
    sys.exit(main())
