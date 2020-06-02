""" Main module for the Discord bot application. """

import sys
from typing import Callable, Optional

from spectra_lexer import SpectraOptions
from spectra_lexer.analysis import StenoAnalyzer, Translation, TranslationPairs
from spectra_lexer.console.system import SystemConsole
from spectra_lexer.discord import DiscordMessage, DiscordBot
from spectra_lexer.display import BoardEngine
from spectra_lexer.qt.svg import SVGConverter
from spectra_lexer.resource.rules import StenoRule
from spectra_lexer.search import MatchDict, SearchEngine


class DiscordApplication:
    """ Spectra engine application that accepts string input from Discord users. """

    def __init__(self, search_engine:SearchEngine, analyzer:StenoAnalyzer,
                 board_engine:BoardEngine, svg_converter:SVGConverter, log:Callable[[str], None], *,
                 query_max_chars:int=None, query_trans:dict=None, search_depth=1, board_AR:float=None) -> None:
        self._search_engine = search_engine
        self._analyzer = analyzer
        self._board_engine = board_engine
        self._svg_converter = svg_converter      # Converter for SVG data to PNG (Discord will not embed SVGs.)
        self._log = log                          # Thread-safe logger.
        self._query_max_chars = query_max_chars  # Optional limit for # of characters allowed in a user query string.
        self._query_trans = query_trans or {}    # Translation table to remove characters before searching for words.
        self._search_depth = search_depth        # Maximum number of search results to analyze at once.
        self._board_AR = board_AR                # Optional fixed aspect ratio for board images.

    @staticmethod
    def _best_match(word:str, matches:MatchDict) -> Optional[str]:
        if not matches:
            return None
        if word in matches:
            return word
        key = word.lower()
        if key in matches:
            return key
        for m in matches:
            if key == m.lower():
                return m
        return None

    def _best_translation(self, word:str, matches:MatchDict) -> Translation:
        """ Find the best pairing between a word and its possible stroke matches. """
        match = self._best_match(word, matches)
        if match is None:
            keys = ""
            word = "-" * len(word)
        else:
            keys_seq = matches[match]
            keys = self._analyzer.best_translation(keys_seq, word)
        return keys, word + " "

    def _split_query(self, query:str) -> TranslationPairs:
        """ Do an advanced lookup to get the best strokes for each word in the query. """
        letters = query.translate(self._query_trans)
        words = letters.split()
        search_list = [self._search_engine.search(word, self._search_depth) for word in words]
        if not any(search_list):
            return []
        return [self._best_translation(word, matches) for word, matches in zip(words, search_list)]

    def _analyze_all(self, translations:TranslationPairs) -> StenoRule:
        """ Create a compound rule from each strokes/word pair we found. """
        return self._analyzer.compound_query(translations)

    def _board_png(self, rule:StenoRule) -> bytes:
        """ Generate a board diagram in PNG raster format with good dimensions. """
        board = self._board_engine.draw_rule(rule, aspect_ratio=self._board_AR)
        svg_data = board.encode('utf-8')
        return self._svg_converter.to_png(svg_data)

    def query(self, query:str) -> DiscordMessage:
        """ Parse a user query string and return a Discord bot message, possibly with a board PNG attached. """
        if self._query_max_chars is not None and len(query) > self._query_max_chars:
            return DiscordMessage('Query is too long.')
        translations = self._split_query(query)
        if not translations:
            return DiscordMessage('No suggestions.')
        analysis = self._analyze_all(translations)
        msg = DiscordMessage(f'``{analysis}``')
        png_data = self._board_png(analysis)
        msg.attach_as_file(png_data, "board.png")
        return msg

    def run_console(self) -> int:
        """ Run the application in a debug console. """
        namespace = {k: getattr(self, k) for k in dir(self) if not k.startswith('__')}
        console = SystemConsole.open(namespace)
        console.repl()
        return 0

    def run_bot(self, token:str, cmd_name="spectra") -> int:
        """ Run the application as a Discord bot. """
        if not token:
            self._log("No token given. Opening test console...")
            return self.run_console()
        bot = DiscordBot(token, self._log)
        bot.add_command(cmd_name, self.query)
        self._log("Discord bot started.")
        return bot.run()


def build_app(opts:SpectraOptions) -> DiscordApplication:
    spectra = opts.compile()
    translations_files = opts.translations_paths()
    log = spectra.log
    io = spectra.translations_io
    search_engine = spectra.search_engine
    analyzer = spectra.analyzer
    board_engine = spectra.board_engine
    log("Loading...")
    svg_converter = SVGConverter(background_rgba=(0, 0, 0, 0))
    excluded_chars = r'''#$%&()*+-,.?!/:;<=>@[\]^_`"{|}~'''
    map_to_space = dict.fromkeys(map(ord, excluded_chars), ' ')
    translations = io.load_json_translations(*translations_files)
    # Strip Plover glue and case metacharacters so our search engine has a chance to find the actual text.
    stripped_values = [v.strip(' {<&>}') for v in translations.values()]
    translations = {k: v for k, v in zip(translations, stripped_values) if v}
    search_engine.set_translations(translations)
    return DiscordApplication(search_engine, analyzer, board_engine, svg_converter, log,
                              query_max_chars=100, query_trans=map_to_space, search_depth=3, board_AR=1.5)


def main() -> int:
    opts = SpectraOptions("Run Spectra as a Discord bot.")
    opts.add("token", "", "Discord bot token (REQUIRED).")
    app = build_app(opts)
    return app.run_bot(opts.token)


if __name__ == '__main__':
    sys.exit(main())
