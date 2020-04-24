""" EXPERIMENTAL DISCORD BOT MODULE (dependency on discord.py not declared in setup). """

import io
import sys
from traceback import format_exc
from typing import Callable, Iterable, Optional

import discord
from PyQt5.QtCore import QBuffer, QIODevice
from PyQt5.QtGui import QColor, QImage, QPainter
from PyQt5.QtSvg import QSvgRenderer

from spectra_lexer import Spectra
from spectra_lexer.engine import StenoEngine
from spectra_lexer.resource.rules import StenoRule
from spectra_lexer.util.cmdline import CmdlineOptions


class BotMessage:
    """ Contains all data that makes up a Discord bot's response. """

    def __init__(self, content:str) -> None:
        self._content = content
        self._file = None

    def attach_as_file(self, data:bytes, filename:str) -> None:
        """ Attach an arbitrary string of bytes to this message as a file. """
        fstream = io.BytesIO(data)
        self._file = discord.File(fstream, filename)

    def to_kwargs(self) -> dict:
        """ Return a dict of kwargs for message.channel.send. """
        kwargs = {'content': self._content}
        if self._file is not None:
            kwargs['file'] = self._file
        return kwargs

    def __str__(self) -> str:
        return self._content


class DiscordBot:
    """ Basic Discord bot that accepts commands from users in the form of '!command args' """

    def __init__(self, token:str, logger=print) -> None:
        self._token = token  # Discord bot token.
        self._log = logger   # String callable to log all bot activity.
        self._cmds = {}      # Dict of command callables. Must accept a string and return a bot message.
        self._client = discord.Client()
        self._client.event(self.on_ready)
        self._client.event(self.on_message)

    def add_command(self, name:str, func:Callable[[str], Optional[BotMessage]]) -> None:
        """ Add a named ! command with a callable that will be executed with the remainder of the user's input. """
        self._cmds[name] = func

    def run(self) -> int:
        """ Attempt to connect to Discord with the provided token. """
        self._log('Connecting to Discord...')
        return self._client.run(self._token)

    async def on_ready(self) -> None:
        """ When logged in, just print a success message and wait for user input. """
        self._log(f'Logged in as {self._client.user}.')

    async def on_message(self, message:discord.Message) -> None:
        """ Parse user input and execute a command if it isn't our own message, it starts with a "!",
            and the characters after the "!" but before whitespace match a registered command. """
        if message.author == self._client.user:
            return
        content = message.content
        if not content.startswith("!"):
            return
        cmd_name, *cmd_body = content[1:].split(None, 1)
        cmd_func = self._cmds.get(cmd_name)
        if cmd_func is None:
            return
        arg_string = cmd_body[0].strip() if cmd_body else ""
        self._log(f"Command: {cmd_name} {arg_string}")
        try:
            reply = cmd_func(arg_string)
            self._log(f"Reply: {reply}")
        except Exception:
            reply = BotMessage('Command parse error.')
            self._log(format_exc())
        if reply is None:
            return
        kwargs = reply.to_kwargs()
        await message.channel.send(**kwargs)


class DiscordApplication:
    """ Spectra engine application that accepts string input from Discord users. """

    BOARD_BG_COLOR = QColor(0, 0, 0, 0)  # Transparent color to use for board PNG backgrounds.
    BOARD_ASPECT_RATIO = 1.5             # Fixed aspect ratio to make board images look best on Discord.
    QUERY_MAX_CHARS = 100                # Maximum number of characters allowed in a user query string.
    ANALYSIS_DELIMS = ["->", "→"]        # Tokens that indicate (and delimit) a strokes -> words analysis.
    EXCLUDED_CHARS = ",.?!"              # Characters that should be removed before searching for words.

    def __init__(self, engine:StenoEngine, space_rule:StenoRule) -> None:
        self._engine = engine          # Main query engine.
        self._space_rule = space_rule  # Stroke separator rule corresponding to space.

    def _svg_to_png(self, svg_data:bytes) -> bytes:
        """ Render SVG bytes on a transparent bitmap image and convert it to a PNG stream.
            Use the viewbox dimensions as pixel sizes. """
        svg = QSvgRenderer(svg_data)
        viewbox = svg.viewBox().size()
        im = QImage(viewbox, QImage.Format_ARGB32)
        im.fill(self.BOARD_BG_COLOR)
        with QPainter(im) as p:
            svg.render(p)
        buf = QBuffer()
        buf.open(QIODevice.WriteOnly)
        im.save(buf, "PNG")
        return buf.data()

    def _board_from_rule(self, rule:StenoRule) -> bytes:
        """ Generate a board diagram in PNG raster format with good dimensions. """
        board = self._engine.generate_board(rule, aspect_ratio=self.BOARD_ASPECT_RATIO)
        svg_data = board.encode('utf-8')
        png_data = self._svg_to_png(svg_data)
        return png_data

    def _reply(self, content:str, rule:StenoRule=None) -> BotMessage:
        """ Construct a Discord bot message from a content string and optionally a rule. """
        msg = BotMessage(content)
        if rule is not None:
            png_data = self._board_from_rule(rule)
            msg.attach_as_file(png_data, "board.png")
        return msg

    @staticmethod
    def _join_rules(rules:Iterable[StenoRule]) -> StenoRule:
        """ Join several rules into one for display purposes. """
        analysis = StenoRule.analysis("", "", "Compound analysis.")
        offset = 0
        for r in rules:
            analysis.keys += r.keys
            analysis.letters += r.letters
            length = len(r.letters)
            analysis.add_connection(r, offset, length)
            offset += length
        return analysis

    def _sanitize(self, letters:str) -> str:
        """ Render a string of letters suitable for piece-by-piece word analysis. """
        for c in self.EXCLUDED_CHARS:
            letters = letters.replace(c, "")
        return letters.lower()

    def _analyze_words(self, letters:str) -> Optional[StenoRule]:
        """ Do an advanced lookup to put together rules containing strokes for multiple words. """
        letters = self._sanitize(letters)
        rules = []
        is_invalid = True
        for word in letters.split():
            matches = self._engine.search(word, 1).matches
            if not matches:
                rule = StenoRule.analysis("?", "-" * len(word), "Skipped word.")
            else:
                is_invalid = False
                pairs = [(s, match) for match, strokes_list in matches.items() for s in strokes_list]
                translation = self._engine.best_translation(*pairs)
                rule = self._engine.analyze(*translation)
            rules += [rule, self._space_rule]
        if is_invalid:
            return None
        rules.pop()
        return self._join_rules(rules)

    def _analyze_translation(self, keys:str, letters:str) -> Optional[StenoRule]:
        """ Do a standard lexical analysis and return the result (unless one or both inputs was empty). """
        keys = keys.strip()
        letters = letters.strip()
        if keys and letters:
            return self._engine.analyze(keys, letters)

    def exec(self, query:str) -> BotMessage:
        """ Parse a user query string and return a Discord bot message. """
        if len(query) > self.QUERY_MAX_CHARS:
            return self._reply('Query is too long.')
        for delim in self.ANALYSIS_DELIMS:
            if delim in query:
                analysis = self._analyze_translation(*query.split(delim, 1))
                if analysis is None:
                    return self._reply('Invalid arguments for -> analysis.')
                return self._reply(f'Analysis: {analysis}', analysis)
        analysis = self._analyze_words(query)
        if analysis is None:
            return self._reply('No suggestions.')
        return self._reply(f'Suggestion: {analysis}', analysis)


def main() -> int:
    opts = CmdlineOptions("Run Spectra as a Discord bot.")
    opts.add("token", "", "Discord bot token (REQUIRED).")
    spectra = Spectra(opts)
    spectra.log("Loading...")
    engine = spectra.build_engine()
    translations_files = spectra.translations_paths()
    engine.load_translations(*translations_files)
    space_rule = engine.analyze("/", " ")
    app = DiscordApplication(engine, space_rule)
    bot = DiscordBot(opts.token, spectra.log)
    bot.add_command("spectra", app.exec)
    return bot.run()


if __name__ == '__main__':
    sys.exit(main())
