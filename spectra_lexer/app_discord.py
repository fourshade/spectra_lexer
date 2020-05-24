""" Main module for the Discord bot application. """

import sys
from typing import Iterable, Optional

from spectra_lexer import Spectra
from spectra_lexer.discord import BotMessage, DiscordBot
from spectra_lexer.engine import StenoEngine
from spectra_lexer.qt.svg import SVGConverter
from spectra_lexer.resource.rules import StenoRule
from spectra_lexer.search import MatchDict
from spectra_lexer.util.cmdline import CmdlineOptions


class DiscordApplication:
    """ Spectra engine application that accepts string input from Discord users. """

    def __init__(self, engine:StenoEngine, svg_converter:SVGConverter, *,
                 query_max_chars:int=None, query_trans:dict=None, search_depth=1, board_AR:float=None) -> None:
        self._engine = engine                    # Main query engine.
        self._svg_converter = svg_converter      # Converter for SVG data to PNG (Discord will not embed SVGs.)
        self._query_max_chars = query_max_chars  # Optional limit for # of characters allowed in a user query string.
        self._query_trans = query_trans or {}    # Translation table to remove characters before searching for words.
        self._search_depth = search_depth        # Maximum number of search results to analyze at once.
        self._board_AR = board_AR                # Optional fixed aspect ratio for board images.

    def _new_rule(self, word:str, matches:MatchDict) -> StenoRule:
        """ Make a new rule from a word and its possible stroke matches. """
        if not matches:
            return StenoRule("?", "-" * len(word), "Skipped word.")
        if word in matches:
            pairs = [(s, word) for s in matches[word]]
        elif word.lower() in matches:
            pairs = [(s, word) for s in matches[word.lower()]]
        else:
            pairs = [(s, match) for match, strokes_list in matches.items() for s in strokes_list]
        translation = self._engine.best_translation(pairs)
        return self._engine.analyze(*translation)

    @staticmethod
    def _join_rules(rules:Iterable[StenoRule]) -> StenoRule:
        """ Join several rules into one for display purposes. """
        analysis = StenoRule("", "", "Compound analysis.")
        offset = 0
        for r in rules:
            analysis.keys += r.keys
            analysis.letters += r.letters
            length = len(r.letters)
            analysis.add_connection(r, offset, length)
            offset += length
        return analysis

    def _analyze_words(self, query:str) -> Optional[StenoRule]:
        """ Do an advanced lookup to put together rules containing strokes for multiple words. """
        letters = query.translate(self._query_trans)
        words = letters.split()
        search_list = [self._engine.search(word, self._search_depth) for word in words]
        if not any(search_list):
            return None
        rules = []
        space_rule = StenoRule("/", " ", "")
        for word, matches in zip(words, search_list):
            rule = self._new_rule(word, matches)
            rules += [rule, space_rule]
        rules.pop()
        return self._join_rules(rules)

    def _board_png(self, rule:StenoRule) -> bytes:
        """ Generate a board diagram in PNG raster format with good dimensions. """
        board = self._engine.generate_board(rule, aspect_ratio=self._board_AR)
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
    opts = CmdlineOptions("Run Spectra as a Discord bot.")
    opts.add("token", "", "Discord bot token (REQUIRED).")
    spectra = Spectra(opts)
    spectra.log("Loading...")
    engine = spectra.build_engine()
    translations_files = spectra.translations_paths()
    engine.load_translations(*translations_files)
    svg_converter = SVGConverter(background_rgba=(0, 0, 0, 0))
    excluded_chars = r'''#$%&()*+-,.?!/:;<=>@[\]^_`"{|}~'''
    map_to_space = dict.fromkeys(map(ord, excluded_chars), ' ')
    app = DiscordApplication(engine, svg_converter,
                             query_max_chars=100, query_trans=map_to_space, search_depth=3, board_AR=1.5)
    bot = DiscordBot(opts.token, spectra.log)
    bot.add_command("spectra", app.exec)
    return bot.run()


if __name__ == '__main__':
    sys.exit(main())
