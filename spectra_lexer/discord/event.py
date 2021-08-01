from .gateway import Intents
from .logger import log


class EventHandler:
    """ Contains coroutine methods to handle named Discord events.
        Method signature format:
            async def on_{event_name_lowercase}(self, data:dict) -> None: """

    def required_intents(self) -> int:
        return 0


class DiscordCommand:
    """ Interface for an application that may respond to a Discord text command. """

    async def run(self, channel_id:str, text:str) -> None:
        raise NotImplementedError


class CommandDispatcher(EventHandler):
    """ Basic Discord bot that accepts commands from users in the form of '!command args' """

    def __init__(self) -> None:
        self._cmds = {}      # Dict of command applications.
        self._user_id = 0    # ID of the connected user. 0 if not logged in.

    def add_command(self, name:str, app:DiscordCommand) -> None:
        """ Add a named ! command that will be executed with the remainder of the user's input. """
        self._cmds[name] = app

    def required_intents(self) -> int:
        return Intents.GUILD_MESSAGES

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
            await cmd_app.run(message['channel_id'], arg_string)
        except Exception:
            log.exception('COMMAND EXCEPTION')
