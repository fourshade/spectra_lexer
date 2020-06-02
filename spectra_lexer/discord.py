""" EXPERIMENTAL DISCORD BOT MODULE (dependency on discord.py not declared in setup). """

import io
from traceback import format_exc
from typing import Callable, Optional

import discord


class DiscordMessage:
    """ Contains all data that makes up a Discord text channel message. """

    def __init__(self, content:str) -> None:
        self._content = content
        self._file = None

    def __str__(self) -> str:
        return self._content

    def attach_as_file(self, data:bytes, filename:str) -> None:
        """ Attach an arbitrary string of bytes to this message as a file. """
        fstream = io.BytesIO(data)
        self._file = discord.File(fstream, filename)

    async def send(self, channel:discord.TextChannel) -> None:
        """ Send the message to a Discord text channel. """
        await channel.send(self._content, file=self._file)


class DiscordBot:
    """ Basic Discord bot that accepts commands from users in the form of '!command args' """

    def __init__(self, token:str, logger=print) -> None:
        self._token = token  # Discord bot token.
        self._log = logger   # String callable to log all bot activity.
        self._cmds = {}      # Dict of command callables. Must accept a string and return a bot message.
        self._client = discord.Client()
        self._client.event(self.on_ready)
        self._client.event(self.on_message)

    def add_command(self, name:str, func:Callable[[str], Optional[DiscordMessage]]) -> None:
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
            reply = DiscordMessage('Command parse error.')
            self._log(format_exc())
        if reply is None:
            return
        await reply.send(message.channel)
