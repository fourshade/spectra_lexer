""" Main module for the Discord bot application. """

import sys
from typing import Iterator, Optional

from spectra_lexer import Spectra, SpectraOptions
from spectra_lexer.console import introspect
from spectra_lexer.qt.svg import SVGEngine
from spectra_lexer.resource.rules import StenoRule
from spectra_lexer.spc_board import BoardDiagram, BoardEngine
from spectra_lexer.spc_lexer import StenoAnalyzer
from spectra_lexer.spc_search import SearchEngine
from spectra_lexer.util.discord import DiscordBot, DiscordMessage


class DiscordApplication:
    """ Spectra engine application that accepts string input from Discord users. """

    FILLER_CHAR = "-"        # Replaces all characters in a word with no matches.
    TR_DELIMS = ["→", "->"]  # Possible delimiters between strokes and text in a query. Captions use the first one.

    def __init__(self, search_engine:SearchEngine, analyzer:StenoAnalyzer,
                 board_engine:BoardEngine, svg_engine:SVGEngine, key_sep:str, *,
                 msg_cls=DiscordMessage, query_max_chars:int=None, board_AR:float=None) -> None:
        self._search_engine = search_engine
        self._analyzer = analyzer
        self._board_engine = board_engine
        self._svg_engine = svg_engine
        self._key_sep = key_sep
        self._msg_cls = msg_cls                  # Factory for Discord messages.
        self._query_max_chars = query_max_chars  # Optional limit for # of characters allowed in a user query string.
        self._board_AR = board_AR                # Optional fixed aspect ratio for board images.

    def _text_message(self, message:str) -> DiscordMessage:
        """ Generate a Discord message consisting only of text. """
        return self._msg_cls(message)

    def _board_message(self, caption:str, board_data:BoardDiagram) -> DiscordMessage:
        """ Generate a Discord message with a literal caption and a board diagram.
            Discord will not embed SVGs directly, so use PNG raster format. """
        msg = self._msg_cls(f'``{caption}``')
        self._svg_engine.loads(board_data)
        png_data = self._svg_engine.encode_image(fmt="PNG")
        msg.attach_as_file(png_data, "board.png")
        return msg

    def _find_rules(self, query:str) -> Iterator[StenoRule]:
        """ Do an advanced lookup and yield an analysis using the best strokes paired with each phrase in <query>.
            Use filler text to replace phrases without any matches. """
        results = self._search_engine.split_search(query, self._key_sep, find_phrases=True)
        for phrase, matches in results:
            if not matches:
                keys = ""
                phrase = self.FILLER_CHAR * len(phrase)
            else:
                keys = self._analyzer.best_translation(matches, phrase)
            yield self._analyzer.query(keys, phrase)

    def _query_search(self, query:str) -> StenoRule:
        """ Parse a user query string as English text and analyze each strokes/phrase pair we find. """
        rules = self._find_rules(query)
        return self._analyzer.join(rules)

    def _query_delimited(self, query:str, delim:str) -> StenoRule:
        """ Parse a user query string as delimited strokes and English text. """
        keys, letters = query.split(delim, 1)
        return self._analyzer.query(keys.strip(), letters.strip())

    def _query(self, query:str) -> StenoRule:
        """ Parse a user query string using the steno analyzer. """
        for delim in self.TR_DELIMS:
            if delim in query:
                return self._query_delimited(query, delim)
        return self._query_search(query)

    def run(self, query:str) -> Optional[DiscordMessage]:
        """ Parse a user query string and return a Discord bot message, possibly with a board PNG attached. """
        query = query.strip()
        if not query:
            return None
        if self._query_max_chars is not None and len(query) > self._query_max_chars:
            return self._text_message('Query is too long.')
        first, *others = query.split(None, 1)
        if not others and first == first.upper():
            keys = self._analyzer.normalize_keys(first)
            if keys:
                board_data = self._board_engine.draw_keys(keys, aspect_ratio=self._board_AR)
                return self._board_message(keys, board_data)
        analysis = self._query(query)
        if analysis.keys:
            show_letters = not query.startswith('+')
            caption = f'{analysis.keys} {self.TR_DELIMS[0]} {analysis.letters}'
            board_data = self._board_engine.draw_rule(analysis, aspect_ratio=self._board_AR, show_letters=show_letters)
            return self._board_message(caption, board_data)
        return self._text_message('No suggestions.')


def build_app(spectra:Spectra) -> DiscordApplication:
    io = spectra.resource_io
    search_engine = spectra.search_engine
    analyzer = spectra.analyzer
    board_engine = spectra.board_engine
    svg_engine = SVGEngine(background_rgba=(0, 0, 0, 0))
    key_sep = spectra.keymap.sep
    translations = io.load_json_translations(*spectra.translations_paths)
    # Strip Plover glue and case metacharacters so our search engine has a chance to find the actual text.
    stripped_values = [v.strip(' {<&>}') for v in translations.values()]
    translations = {k: v for k, v in zip(translations, stripped_values) if v}
    search_engine.set_translations(translations)
    return DiscordApplication(search_engine, analyzer, board_engine, svg_engine, key_sep,
                              query_max_chars=100, board_AR=1.5)


def main() -> int:
    """ Run the application as a Discord bot. """
    opts = SpectraOptions("Run Spectra as a Discord bot.")
    opts.add("token", "", "Discord bot token (REQUIRED).")
    opts.add("command", "spectra", "!command string for Discord users.")
    spectra = Spectra(opts)
    log = spectra.logger.log
    log("Loading Discord bot...")
    app = build_app(spectra)
    if not opts.token:
        log("No token given. Opening test console...")
        return introspect(app)
    bot = DiscordBot(opts.token, log)
    bot.add_command(opts.command, app.run)
    log("Discord bot started.")
    return bot.run()


if __name__ == '__main__':
    sys.exit(main())
