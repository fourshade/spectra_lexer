""" EXPERIMENTAL DISCORD BOT MODULE (dependency on discord.py not declared in setup). """

import io
import sys
from traceback import format_exc
from typing import Optional, Tuple

import discord
from PyQt5.QtCore import QBuffer, QIODevice
from PyQt5.QtGui import QColor, QImage, QPainter
from PyQt5.QtSvg import QSvgRenderer

from spectra_lexer.base import Spectra
from spectra_lexer.engine import StenoEngine
from spectra_lexer.resource.rules import StenoRule
from spectra_lexer.util.cmdline import CmdlineOptions


def svg_to_png(svg_data:bytes, bg_color=QColor(0, 0, 0, 0)) -> bytearray:
    """ Render SVG bytes on a transparent bitmap image and convert it to a PNG stream.
        Use the viewbox dimensions as pixel sizes. """
    svg = QSvgRenderer(svg_data)
    viewbox = svg.viewBox().size()
    im = QImage(viewbox, QImage.Format_ARGB32)
    im.fill(bg_color)
    with QPainter(im) as p:
        svg.render(p)
    buf = QBuffer()
    buf.open(QIODevice.WriteOnly)
    im.save(buf, "PNG")
    return buf.data()


class DiscordBot:

    ARG_DELIMS = ["->", "→"]

    def __init__(self, engine:StenoEngine, token:str, logger=print) -> None:
        self._engine = engine
        self._token = token
        self._log = logger
        self._client = discord.Client()
        self._client.event(self.on_ready)
        self._client.event(self.on_message)

    def run(self) -> int:
        self._log('Connecting to Discord...')
        return self._client.run(self._token)

    async def on_ready(self) -> None:
        self._log(f'Logged in as {self._client.user}')

    async def on_message(self, message:discord.Message) -> None:
        if message.author == self._client.user:
            return
        content = message.content
        for delim in self.ARG_DELIMS:
            if delim in content:
                args = [p.strip() for p in content.split(delim)]
                if len(args) != 2 or not all(args):
                    return
                try:
                    msg, kwargs = self.handle_query(*args)
                    await message.channel.send(msg, **kwargs)
                except Exception:
                    self._log(format_exc())
                    await message.channel.send('Parse Error.')
                return

    def handle_query(self, keys:str, letters:str) -> Tuple[str, dict]:
        if len(keys) > 30 or len(letters) > 100:
            return 'Query is too long.', {}
        self._log(f'Parsing {keys} -> {letters}')
        if "?" in keys:
            rule = self.lookup_phrase(letters)
            if rule is None:
                return 'No suggestions.', {}
            msg = f'Suggestion: {rule}'
        else:
            rule = self._engine.analyze(keys, letters)
            msg = f'Analysis: {rule}'
        board = self._engine.generate_board(rule, aspect_ratio=1.5)
        svg_data = board.encode('utf-8')
        png_data = svg_to_png(svg_data)
        f = discord.File(io.BytesIO(png_data), "board.png")
        return msg, {"file": f}

    def lookup_phrase(self, letters:str) -> Optional[StenoRule]:
        subrules = []
        letters = letters.lower().replace(",", "").replace(".", "").replace("?", "").replace("!", "")
        for word in letters.split():
            matches = self._engine.search(word, 1).matches
            if not matches:
                return None
            pairs = [(s, match) for match, strokes_list in matches.items() for s in strokes_list]
            rule = self._engine.analyze_best(*pairs)
            subrules.append(rule)
        rule, *others = subrules
        if others:
            offset = len(rule.keys)
            sep = self._engine.analyze("/", " ")
            for oth in others:
                for r in (sep, oth):
                    rule.keys += r.keys
                    rule.letters += r.letters
                    for item in r:
                        rule.add_connection(item.child, item.start + offset, item.length)
                    offset += len(r.keys)
        return rule


def main() -> int:
    opts = CmdlineOptions("Run Spectra as a Discord bot.")
    opts.add("token", "", "Discord bot token (REQUIRED).")
    spectra = Spectra(opts)
    spectra.log("Loading...")
    engine = spectra.build_engine()
    translations_files = spectra.translations_paths()
    engine.load_translations(*translations_files)
    bot = DiscordBot(engine, opts.token, spectra.log)
    return bot.run()


if __name__ == '__main__':
    sys.exit(main())
