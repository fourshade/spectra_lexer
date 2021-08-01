""" Main module for the Discord bot application. """

import sys

from spectra_lexer import Spectra, SpectraOptions
from spectra_lexer.app_discord import build_app, DiscordApplication, QueryError, QueryPage
from spectra_lexer.console import introspect
from spectra_lexer.discord.client import Client
from spectra_lexer.discord.event import CommandDispatcher, DiscordCommand
from spectra_lexer.discord.http import HTTPClient
from spectra_lexer.discord.logger import log
from spectra_lexer.discord.request import CreateFormMessageRequest, CreateMessageRequest


class DiscordBot(DiscordCommand):

    def __init__(self, app:DiscordApplication, http:HTTPClient) -> None:
        self._app = app
        self._http = http

    async def _send_error(self, channel_id:str, error:str) -> None:
        """ Send a Discord message with some error text. """
        req = CreateMessageRequest(channel_id, error)
        await self._http.request(req)
        log.info("Error: " + error)

    async def _send_page(self, channel_id:str, page:QueryPage) -> None:
        """ Send a Discord message with a single board diagram. """
        caption = page.description
        req = CreateFormMessageRequest(channel_id, f'``{caption}``')
        req.attach_file(page.png_diagram, "board.png", "image/png")
        await self._http.request(req)
        log.info("Reply: " + caption)

    async def run(self, channel_id:str, text:str) -> None:
        try:
            page, *more_pages = self._app.run(text)
            if more_pages:
                show_letters = not text.startswith('+')
                page = more_pages[show_letters]
            await self._send_page(channel_id, page)
        except QueryError as e:
            await self._send_error(channel_id, ', '.join(e.args))
        except Exception:
            await self._send_error(channel_id, 'Internal error.')
            raise


def main() -> int:
    """ Run the application as a Discord bot. """
    opts = SpectraOptions("Run Spectra as a Discord bot.")
    opts.add("token", "", "Discord bot token (REQUIRED).")
    opts.add("command", "spectra", "!command string for Discord users.")
    spectra = Spectra(opts)
    # Hackish way to log all bot activity to one callable.
    log.line_logger = spectra.logger.log
    log.info("Loading Discord bot...")
    app = build_app(spectra, 400, 300, max_chars=100)
    token = opts.token.strip()
    if not token:
        log.info("No token given. Opening test console...")
        return introspect(app)
    http = HTTPClient(token)
    bot = DiscordBot(app, http)
    cmds = CommandDispatcher()
    cmds.add_command(opts.command, bot)
    client = Client(http, token)
    client.add_event_handler(cmds)
    log.info("Discord bot started.")
    client.run()
    return 0


if __name__ == '__main__':
    sys.exit(main())
