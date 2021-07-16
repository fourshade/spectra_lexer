""" Main module for the Discord bot application. """

import sys
from typing import Optional

from PyQt5.QtCore import QBuffer, QIODevice, QRectF
from PyQt5.QtGui import QColor, QImage, QPainter
from PyQt5.QtSvg import QSvgRenderer

from spectra_lexer import Spectra, SpectraOptions
from spectra_lexer.console import introspect
from spectra_lexer.resource.rules import StenoRule
from spectra_lexer.spc_board import BoardDiagram, BoardEngine
from spectra_lexer.spc_lexer import StenoAnalyzer
from spectra_lexer.spc_search import SearchEngine
from spectra_lexer.util.discord import DiscordBot, DiscordMessage


class SVGRasterizer:
    """ Renders SVG data to raster images. """

    def __init__(self, w_max:int, h_max:int, *, bg_color=QColor(0, 0, 0, 0)) -> None:
        self._w_max = w_max        # Limit on image width in pixels.
        self._h_max = h_max        # Limit on image height in pixels.
        self._bg_color = bg_color  # Color to use for raster backgrounds.

    def encode(self, svg_data:str, fmt="PNG") -> bytes:
        """ Create a new bitmap image with the current background color and render an SVG image to it.
            Pixel dimensions will fit the viewbox at maximum scale.
            Convert the image to a data stream and return the raw bytes. """
        svg = QSvgRenderer(svg_data.encode("utf8"))
        v_size = svg.viewBox().size()
        vw = v_size.width()
        vh = v_size.height()
        scale = min(self._w_max / vw, self._h_max / vh)
        w = round(vw * scale)
        h = round(vh * scale)
        im = QImage(w, h, QImage.Format_ARGB32)
        im.fill(self._bg_color)
        with QPainter(im) as p:
            p.setRenderHints(QPainter.Antialiasing)
            svg.render(p, QRectF(0, 0, w, h))
        buf = QBuffer()
        buf.open(QIODevice.WriteOnly)
        im.save(buf, fmt)
        return buf.data()


class DiscordApplication:
    """ Spectra engine application that accepts string input from Discord users. """

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

    def run(self, query:str) -> Optional[DiscordMessage]:
        """ Parse a user query string and return a Discord bot message, possibly with a board PNG attached. """
        query = query.strip()
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
    return DiscordApplication(search_engine, analyzer, board_engine, rasterizer,
                              split_trans=split_trans, query_max_chars=100, board_AR=400/300)


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
