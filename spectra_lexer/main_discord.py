""" Main module for the Discord bot application. """

import sys
from typing import Iterable

from spectra_lexer import Spectra, SpectraOptions
from spectra_lexer.app_discord import build_app, DiscordApplication, QueryError, QueryPage, QueryResult
from spectra_lexer.console import introspect
from spectra_lexer.discord.client import Client
from spectra_lexer.discord.event import CommandDispatcher, DiscordCommand, EventHandler
from spectra_lexer.discord.http import HTTPClient, HTTPException
from spectra_lexer.discord.logger import log
from spectra_lexer.discord.request import CreateFormMessageRequest, CreateMessageRequest, \
    CreateInteractionResponseRequest, EditMessageRequest

WARNING_FOOTER = """NOTE: Interactive buttons are an experimental feature.
If the bot is lagging or the message is too old, they may fail or disappear."""


def _embed(page:QueryPage, image_url:str=None, footer:str=None) -> dict:
    embed = {
        "title": page.title,
        "description": f'```{page.description}```'
    }
    if image_url is not None:
        embed["image"] = {"url": image_url}
    if footer is not None:
        embed["footer"] = {"text": footer}
    return embed


def _button_row(labels:Iterable[str], current_label:str=None) -> dict:
    return {
        "type": 1,  # ACTION_ROW
        "components": [
            {
                "type": 2,  # BUTTON
                "label": s,
                "style": 1,  # PRIMARY
                "custom_id": s,
                "disabled": s == current_label
            }
            for s in labels
        ]
    }


class DiscordBot(DiscordCommand, EventHandler):

    def __init__(self, app:DiscordApplication, http:HTTPClient, cache_channel_id='') -> None:
        self._app = app
        self._http = http
        self._cache_channel_id = cache_channel_id
        self._embed_cache = {}

    async def _send_error(self, channel_id:str, error:str) -> None:
        """ Send a Discord message with some error text. """
        req = CreateMessageRequest(channel_id)
        req["content"] = error
        await self._http.request(req)
        log.info(f'Error: {error}')

    async def _send_page(self, channel_id:str, page:QueryPage) -> None:
        """ Send a Discord message with a single page. Does not require a cache channel. """
        req = CreateFormMessageRequest(channel_id)
        data = page.png_diagram
        if data is None:
            embed = _embed(page)
        else:
            filename = "board.png"
            req.attach_file(data, filename, "image/png")
            embed = _embed(page, "attachment://" + filename)
        req["embeds"] = [embed]
        await self._http.request(req)
        log.info(f'Reply: {embed}')

    async def _send_interactive(self, channel_id:str, pages:QueryResult, start_idx=0) -> None:
        """ Send an interactive Discord message with multiple pages. Requires a cache channel. """
        cache_req = CreateFormMessageRequest(self._cache_channel_id)
        for i, p in enumerate(pages):
            data = p.png_diagram
            if data is not None:
                cache_req.attach_file(data, f"{i}.png", "image/png")
        cache_message = await self._http.request(cache_req)
        urls = [a["url"] for a in cache_message["attachments"]]
        log.info(f"Sent {len(urls)} images to cache channel.")
        it = iter(urls)
        embed_map = {p.title: _embed(p, next(it) if p.png_diagram is not None else None, WARNING_FOOTER) for p in pages}
        start_label = pages[start_idx].title
        req = CreateMessageRequest(channel_id)
        req["embeds"] = [embed_map[start_label]]
        req["components"] = [_button_row(embed_map, start_label)]
        message = await self._http.request(req)
        message_id = message['id']
        self._embed_cache[message_id] = embed_map
        log.info(f'Interactive reply: {len(pages)} pages, id={message_id}')

    async def run(self, channel_id:str, text:str) -> None:
        try:
            pages = self._app.run(text)
            if len(pages) > 1 and self._cache_channel_id:
                await self._send_interactive(channel_id, pages, 1)
                return
            page, *more_pages = pages
            if more_pages:
                show_letters = not text.startswith('+')
                page = more_pages[show_letters]
            await self._send_page(channel_id, page)
        except QueryError as e:
            await self._send_error(channel_id, ', '.join(e.args))
        except Exception:
            await self._send_error(channel_id, 'Internal error.')
            raise

    async def on_interaction_create(self, interaction:dict) -> None:
        if not interaction["type"] == 3:  # MESSAGE_COMPONENT
            return
        custom_id = interaction["data"]["custom_id"]
        message_id = interaction["message"]["id"]
        embed_map = self._embed_cache.get(message_id)
        if embed_map is not None and custom_id not in embed_map:
            # If we have a good message reference with a bad id, just ignore it.
            return
        req = CreateInteractionResponseRequest(interaction_id=interaction["id"], interaction_token=interaction["token"])
        req["type"] = 6  # DEFERRED_UPDATE_MESSAGE
        req["data"] = {"flags": 64}  # EPHEMERAL
        try:
            await self._http.request(req)
        except HTTPException:
            # Remove the buttons if we can't handle the traffic.
            embed_map = None
        log.info(f'Interaction: {custom_id} @ {message_id}')
        req = EditMessageRequest(interaction["channel_id"], message_id)
        if embed_map is None:
            # Remove the buttons if we can't find data for the pages (i.e. they are too old).
            custom_id = None
            req["components"] = []
        else:
            # Switch to the requested page and move the disabled flag to that button.
            req["embeds"] = [embed_map[custom_id]]
            req["components"] = [_button_row(embed_map, custom_id)]
        await self._http.request(req)
        log.info(f'Set page: {custom_id} @ {message_id}')


def main() -> int:
    """ Run the application as a Discord bot. """
    opts = SpectraOptions("Run Spectra as a Discord bot.")
    opts.add("token", "", "Discord bot token (REQUIRED).")
    opts.add("command", "spectra", "!command string for Discord users.")
    opts.add("cache_id", "", "Optional channel ID for image cache.")
    spectra = Spectra(opts)
    log.setHandler(spectra.logger.log)
    log.info("Loading Discord bot...")
    app = build_app(spectra, 400, 300, max_chars=100)
    token = opts.token.strip()
    if not token:
        log.info("No token given. Opening test console...")
        return introspect(app)
    http = HTTPClient(token)
    bot = DiscordBot(app, http, opts.cache_id)
    cmds = CommandDispatcher()
    cmds.add_command(opts.command, bot)
    client = Client(http, token)
    client.add_event_handler(cmds)
    client.add_event_handler(bot)
    log.info("Discord bot started.")
    client.start()
    return 0


if __name__ == '__main__':
    sys.exit(main())
