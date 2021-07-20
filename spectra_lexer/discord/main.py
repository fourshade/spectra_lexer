from typing import Optional

from .client import Client, EventHandler
from .http import FileData
from .logger import log, LineLogger


class DiscordMessage:
    """ Contains all data that makes up a reply to a Discord text channel. """

    def __init__(self, content:str) -> None:
        self.content = content  # Text content of the message.
        self.files = []         # Optional file attachments.

    def __str__(self) -> str:
        s = repr(self.content)
        if self.files:
            size = sum([len(f.data) for f in self.files])
            s += f' + {size} bytes'
        return s

    def __repr__(self) -> str:
        return f'<Message: {self}>'

    def attach_file(self, data:bytes, filename:str) -> None:
        """ Attach an arbitrary string of bytes to this message as a file. """
        if len(self.files) >= 10:
            raise ValueError('Cannot attach more than 10 files')
        self.files.append(FileData(data, filename))

    def get_payload(self) -> dict:
        return {"allowed_mentions": {"parse": []},
                "content": self.content}


class DiscordApplication:
    """ Interface for an application that may (or may not) respond to a Discord text command with a message. """

    def run(self, text:str) -> Optional[DiscordMessage]:
        raise NotImplementedError


class DiscordBot(EventHandler):
    """ Basic Discord bot that accepts commands from users in the form of '!command args' """

    def __init__(self, token:str, logger:LineLogger=None) -> None:
        self._cmds = {}      # Dict of command applications.
        self._user_id = 0    # ID of the connected user. 0 if not logged in.
        if logger is not None:
            # Hackish way to log all bot activity to one callable.
            log.line_logger = logger
        self._client = Client(token)
        self._client.add_event_handler(self)

    def add_command(self, name:str, app:DiscordApplication) -> None:
        """ Add a named ! command with an app that will be executed with the remainder of the user's input. """
        self._cmds[name] = app

    def run(self) -> int:
        """ Attempt to connect to Discord with the provided token. """
        log.info('Connecting to Discord...')
        try:
            self._client.run()
            return 0
        except Exception:
            log.exception('CLIENT EXCEPTION')
        return 1

    async def on_ready(self, data:dict) -> None:
        """ When logged in, just print a success message and wait for user input. """
        me = data['user']
        self._user_id = me['id']
        username = me['username']
        log.info(f'Logged in as {username}.')

    async def on_message_create(self, message:dict) -> None:
        """ Parse user input and execute a command if it isn't our own message, it starts with a "!",
            and the characters after the "!" but before whitespace match a registered command. """
        if message['author']['id'] == self._user_id:
            return
        content = message['content']
        if not content.startswith('!'):
            return
        cmd_name, *cmd_body = content[1:].split(None, 1)
        cmd_app = self._cmds.get(cmd_name)
        if cmd_app is None:
            return
        arg_string = cmd_body[0].strip() if cmd_body else ''
        log.info(f'Command: {cmd_name} {arg_string}')
        try:
            reply = cmd_app.run(arg_string)
            log.info(f'Reply: {reply}')
        except Exception:
            reply = DiscordMessage('Command parse error.')
            log.exception('APPLICATION EXCEPTION')
        if reply is None:
            return
        await self._client.create_message(message['channel_id'], reply.get_payload(), reply.files)
