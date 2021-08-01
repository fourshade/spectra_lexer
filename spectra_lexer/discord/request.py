import io
import json
from typing import Any
from urllib.parse import quote as _uriquote

from aiohttp import FormData


class AbstractRequest:

    BASE = 'https://discord.com/api/v9'

    method: str
    path: str

    def __init__(self, **fields) -> None:
        for k, v in fields.items():
            if isinstance(v, str):
                fields[k] = _uriquote(v)
        self.url = self.BASE + self.path.format(**fields)
        # route parameters
        self._channel_id = fields.get('channel_id')
        self._guild_id = fields.get('guild_id')

    def bucket(self) -> str:
        """ Rate buckets are divided by channel, guild, and route. """
        return f'{self._channel_id}:{self._guild_id}:{self.path}'

    def __str__(self) -> str:
        return f'{self.method} {self.path}'

    def __repr__(self) -> str:
        return f'<Request: {self}>'

    def headers(self) -> dict:
        return {}

    def content(self) -> Any:
        return None

    def reset(self) -> None:
        pass


class GatewayRequest(AbstractRequest):
    """ Get the standard path to the Discord gateway. Requires no authorization. """

    method = 'GET'
    path = '/gateway'


class BotGatewayRequest(AbstractRequest):
    """ Get the bot-specific path to the Discord gateway. Requires bot authorization. """

    method = 'GET'
    path = '/gateway/bot'


class AbstractJSONRequest(AbstractRequest):

    def __init__(self, **fields) -> None:
        super().__init__(**fields)
        self._payload = {}

    def __str__(self) -> str:
        return super().__str__() + f": {self._payload}"

    def headers(self) -> dict:
        """ aiohttp doesn't detect JSON content, so we must set the header manually. """
        return {'Content-Type': 'application/json'}

    def content(self) -> str:
        return json.dumps(self._payload, separators=(',', ':'), ensure_ascii=True)

    def __setitem__(self, name:str, value:Any) -> None:
        self._payload[name] = value


class CreateMessageRequest(AbstractJSONRequest):
    """ Create a standard Discord message. """

    method = 'POST'
    path = '/channels/{channel_id}/messages'

    def __init__(self, channel_id:str, content:str=None, *, allow_mentions=False) -> None:
        super().__init__(channel_id=channel_id)
        if not allow_mentions:
            self["allowed_mentions"] = {"parse": []}
        if content is not None:
            self["content"] = content  # Text content of the message.


class CreateFormMessageRequest(CreateMessageRequest):
    """ Create a Discord message with file attachments (requires form content type). """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._size = 0
        self._files = []

    def __str__(self) -> str:
        return super().__str__() + f' + {self._size} bytes'

    def attach_file(self, data:bytes, filename:str, content_type='application/octet-stream') -> None:
        """ Attach an arbitrary string of bytes to this message as a file. """
        if len(self._files) >= 10:
            raise ValueError('Cannot attach more than 10 files')
        # Dummy out close() in file objects so aiohttp can't disable them.
        fp = io.BytesIO(data)
        fp.close = lambda: None
        self._files.append((fp, filename, content_type))
        self._size += len(data)

    def headers(self) -> dict:
        """ Discord requires this awkward override for aiohttp to set the headers right. """
        return {}

    def content(self) -> FormData:
        """ multipart forms are tricky, but aiohttp does well if we fill in the right blanks. """
        form = FormData()
        form.add_field('payload_json', super().content())
        for i, (fp, filename, content_type) in enumerate(self._files):
            form.add_field(f'file{i}', fp, filename=filename, content_type=content_type)
        return form

    def reset(self) -> None:
        """ Rewind every file object to the start. """
        for fp, *_ in self._files:
            fp.seek(0)


class EditMessageRequest(AbstractJSONRequest):
    """ Edit a standard Discord message. """

    method = 'PATCH'
    path = '/channels/{channel_id}/messages/{message_id}'

    def __init__(self, channel_id:str, message_id:str, *, allow_mentions=False) -> None:
        super().__init__(channel_id=channel_id, message_id=message_id)
        if not allow_mentions:
            self["allowed_mentions"] = {"parse": []}


class CreateInteractionResponseRequest(AbstractJSONRequest):
    """ Create a response to an Interaction from the gateway. """

    method = 'POST'
    path = '/interactions/{interaction_id}/{interaction_token}/callback'
