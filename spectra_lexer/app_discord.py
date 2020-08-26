""" Main module for the Discord bot application. """

import sys
from typing import Iterator, Optional, Sequence

from spectra_lexer import Spectra, SpectraOptions
from spectra_lexer.console import introspect
from spectra_lexer.qt.svg import SVGRasterEngine
from spectra_lexer.resource.rules import StenoRule
from spectra_lexer.spc_board import BoardDiagram, BoardEngine
from spectra_lexer.spc_lexer import StenoAnalyzer
from spectra_lexer.spc_search import SearchEngine
from spectra_lexer.util.discord import DiscordBot, DiscordMessage


class MessageFactory:
    """ Factory for Discord messages containing content from Spectra. """

    def __init__(self, svg_engine:SVGRasterEngine, *, msg_cls=DiscordMessage) -> None:
        self._svg_engine = svg_engine
        self._msg_cls = msg_cls

    def text_message(self, message:str) -> DiscordMessage:
        """ Generate a Discord message consisting only of text. """
        return self._msg_cls(message)

    def board_message(self, caption:str, board_data:BoardDiagram) -> DiscordMessage:
        """ Generate a Discord message with a literal caption and a board diagram.
            Discord will not embed SVGs directly, so use PNG raster format. """
        msg = self._msg_cls(f'``{caption}``')
        self._svg_engine.loads(board_data)
        png_data = self._svg_engine.encode_image(fmt="PNG")
        msg.attach_as_file(png_data, "board.png")
        return msg


class DiscordApplication:
    """ Spectra engine application that accepts string input from Discord users. """

    FILLER_CHAR = "-"        # Replaces all characters in a word with no matches.
    TR_DELIMS = ["→", "->"]  # Possible delimiters between strokes and text in a query. Captions use the first one.

    def __init__(self, search_engine:SearchEngine, analyzer:StenoAnalyzer,
                 board_engine:BoardEngine, msg_factory:MessageFactory, key_sep:str, *,
                 query_max_chars:int=None, query_trans:dict=None, search_depth=1, board_AR:float=None) -> None:
        self._search_engine = search_engine
        self._analyzer = analyzer
        self._board_engine = board_engine
        self._text_message = msg_factory.text_message
        self._board_message = msg_factory.board_message
        self._key_sep = key_sep
        self._query_max_chars = query_max_chars  # Optional limit for # of characters allowed in a user query string.
        self._query_trans = query_trans or {}    # Translation table to remove characters before searching for words.
        self._search_depth = search_depth        # Maximum number of search results to analyze at once.
        self._board_AR = board_AR                # Optional fixed aspect ratio for board images.

    def _find_matches(self, word:str) -> Sequence[str]:
        """ Search for possible stroke matches for a <word>. """
        matches = self._search_engine.search(word, self._search_depth)
        if not matches:
            return ()
        if word in matches:
            return matches[word]
        key = word.lower()
        if key in matches:
            return matches[key]
        for m in matches:
            if key == m.lower():
                return matches[m]
        return ()

    def _missing_word(self, word:str) -> str:
        """ Return filler text to replace a word without any matches. """
        return self.FILLER_CHAR * len(word)

    def _words_to_rules(self, letters:str) -> Iterator[StenoRule]:
        """ Do an advanced lookup and yield an analysis using the best strokes paired with each word in <letters>. """
        for word in letters.split():
            matches = self._find_matches(word)
            if not matches:
                keys = ""
                word = self._missing_word(word)
            else:
                keys = self._analyzer.best_translation(matches, word)
            yield self._analyzer.query(keys, word)

    def _query_search(self, query:str) -> StenoRule:
        """ Parse a user query string as English text and analyze each strokes/word pair we find. """
        letters = query.translate(self._query_trans)
        rules = self._words_to_rules(letters)
        delimited = self._analyzer.delimit(rules, self._key_sep, " ")
        return self._analyzer.join(delimited)

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
    key_sep = spectra.keymap.sep
    svg_engine = SVGRasterEngine(background_rgba=(0, 0, 0, 0))
    msg_factory = MessageFactory(svg_engine)
    excluded_chars = r'''#$%&()*+-,.?!/:;<=>@[\]^_`"{|}~'''
    map_to_space = dict.fromkeys(map(ord, excluded_chars), ' ')
    translations = io.load_json_translations(*spectra.translations_paths)
    # Strip Plover glue and case metacharacters so our search engine has a chance to find the actual text.
    stripped_values = [v.strip(' {<&>}') for v in translations.values()]
    translations = {k: v for k, v in zip(translations, stripped_values) if v}
    search_engine.set_translations(translations)
    return DiscordApplication(search_engine, analyzer, board_engine, msg_factory, key_sep,
                              query_max_chars=100, query_trans=map_to_space, search_depth=3, board_AR=1.5)


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
