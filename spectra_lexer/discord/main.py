import io
from traceback import format_exc
from typing import Callable, Optional

import discord

LineLogger = Callable[[str], None]  # Line-based string callable used for log messages.


class DiscordMessage:
    """ Contains all data that makes up a Discord text channel message. """

    def __init__(self, content:str) -> None:
        self._content = content  # Text content of the message.
        self._files = []         # Optional file attachments.
        self._attach_size = 0    # Total size of attachments in bytes.

    def __str__(self) -> str:
        s = repr(self._content)
        if self._attach_size:
            s += f' + {self._attach_size} bytes'
        return s

    def __repr__(self) -> str:
        return f'<Message: {self}>'

    def attach_file(self, data:bytes, filename:str) -> None:
        """ Attach an arbitrary string of bytes to this message as a file. """
        fstream = io.BytesIO(data)
        file = discord.File(fstream, filename)
        self._files.append(file)
        self._attach_size += len(data)

    async def send(self, channel:discord.TextChannel) -> None:
        """ Send the message to a Discord text channel. """
        await channel.send(self._content, files=(self._files or None))


class DiscordApplication:
    """ Interface for an application that may (or may not) respond to a Discord text command with a message. """

    def run(self, text:str) -> Optional[DiscordMessage]:
        raise NotImplementedError


class DiscordBot:
    """ Basic Discord bot that accepts commands from users in the form of '!command args' """

    def __init__(self, token:str, logger:LineLogger=print) -> None:
        self._token = token  # Discord bot token.
        self._log = logger   # String callable to log all bot activity.
        self._cmds = {}      # Dict of command applications.
        self._client = discord.Client()
        self._client.event(self.on_ready)
        self._client.event(self.on_message)

    def _log_exception(self, source:str) -> None:
        """ Log the current exception under a known source. """
        self._log(source + ' EXCEPTION\n' + format_exc(chain=False))

    def add_command(self, name:str, app:DiscordApplication) -> None:
        """ Add a named ! command with an app that will be executed with the remainder of the user's input. """
        self._cmds[name] = app

    def run(self) -> int:
        """ Attempt to connect to Discord with the provided token. """
        self._log('Connecting to Discord...')
        try:
            self._client.run(self._token)
            return 0
        except Exception:
            self._log_exception('DISCORD CLIENT')
        return 1

    async def on_ready(self) -> None:
        """ When logged in, just print a success message and wait for user input. """
        self._log(f'Logged in as {self._client.user}.')

    async def on_message(self, message:discord.Message) -> None:
        """ Parse user input and execute a command if it isn't our own message, it starts with a "!",
            and the characters after the "!" but before whitespace match a registered command. """
        if message.author == self._client.user:
            return
        content = message.content
        if not content.startswith('!'):
            return
        cmd_name, *cmd_body = content[1:].split(None, 1)
        cmd_app = self._cmds.get(cmd_name)
        if cmd_app is None:
            return
        arg_string = cmd_body[0].strip() if cmd_body else ''
        self._log(f'Command: {cmd_name} {arg_string}')
        try:
            reply = cmd_app.run(arg_string)
            self._log(f'Reply: {reply}')
        except Exception:
            reply = DiscordMessage('Command parse error.')
            self._log_exception('COMMAND')
        if reply is None:
            return
        await reply.send(message.channel)
