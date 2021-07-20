import asyncio
import datetime
import json
import sys
import weakref
from urllib.parse import quote as _uriquote

from aiohttp import __version__ as aiohttp_version, ClientResponse, ClientSession, ClientWebSocketResponse, FormData

from .logger import log


class FileData:
    """ A parameter object used for sending binary data files. """

    __slots__ = ('data', 'filename', 'content_type')

    def __init__(self, data:bytes, filename:str, content_type='application/octet-stream') -> None:
        self.data = data
        self.filename = filename  # Filename to display when uploading to Discord.
        self.content_type = content_type


def _flatten_error_dict(d:dict, key='') -> dict:
    items = {}
    for k, v in d.items():
        new_key = key + '.' + k if key else k
        if not isinstance(v, dict):
            items[new_key] = v
        elif '_errors' in v:
            items[new_key] = ' '.join(x.get('message', '') for x in v['_errors'])
        else:
            items.update(_flatten_error_dict(v, new_key))
    return items


class HTTPException(Exception):
    """ Exception that's thrown when an HTTP request operation fails. """

    def __init__(self, response:ClientResponse, data:dict) -> None:
        self.response = response         # The response of the failed HTTP request.
        self.code = data.get('code', 0)  # Discord specific error code for the failure.
        text = data.get('message', '')
        errors = data.get('errors')
        if errors:
            errors = _flatten_error_dict(errors)
            helpful = '\n'.join('In %s: %s' % t for t in errors.items())
            text += '\n' + helpful
        msg = f'{response.status} {response.reason} (error code: {self.code})'
        if text:
            msg += f': {text}'
        super().__init__(msg)


class Unauthorized(HTTPException):
    """ Exception that's thrown for when status code 401 occurs. """
    pass


class Forbidden(HTTPException):
    """ Exception that's thrown for when status code 403 occurs. """
    pass


class NotFound(HTTPException):
    """ Exception that's thrown for when status code 404 occurs."""
    pass


class DiscordServerError(HTTPException):
    """ Exception that's thrown for when a 500 range status code occurs. """
    pass


class DiscordClientWebSocketResponse(ClientWebSocketResponse):

    async def close(self, *, code=4000, message=b'') -> bool:
        return await super().close(code=code, message=message)


class Route:

    BASE = 'https://discord.com/api/v9'

    def __init__(self, method:str, path:str, **parameters) -> None:
        self.method = method
        self.path = path
        url = self.BASE + path
        if parameters:
            self.url = url.format(**{k: _uriquote(v) if isinstance(v, str) else v for k, v in parameters.items()})
        else:
            self.url = url
        # major parameters:
        self.channel_id = parameters.get('channel_id')
        self.guild_id = parameters.get('guild_id')

    def bucket(self) -> str:
        # the bucket is just method + path w/ major parameters
        return '{0.channel_id}:{0.guild_id}:{0.path}'.format(self)


class _MaybeUnlock:

    def __init__(self, lock:asyncio.Lock) -> None:
        self._lock = lock
        self._unlock = True

    def __enter__(self) -> '_MaybeUnlock':
        return self

    def defer(self) -> None:
        self._unlock = False

    def __exit__(self, *args) -> None:
        if self._unlock:
            self._lock.release()


class HTTPClient:
    """ Represents an HTTP client sending HTTP requests to the Discord API. """

    def __init__(self, token:str) -> None:
        self.token = token  # Raw authentication token.
        self._loop = asyncio.get_event_loop()
        self._session = ClientSession(ws_response_class=DiscordClientWebSocketResponse)
        self._locks = weakref.WeakValueDictionary()
        self._global_over = asyncio.Event()
        self._global_over.set()
        user_agent = 'SpectraBot/0.1 Python/{0} aiohttp/{1}'
        self._user_agent = user_agent.format(sys.version.split()[0], aiohttp_version)

    async def ws_connect(self, url:str) -> ClientWebSocketResponse:
        headers = {'User-Agent': self._user_agent}
        return await self._session.ws_connect(url, max_msg_size=0, timeout=30.0, autoclose=False, headers=headers)

    async def request(self, route:Route, *, json_data:str=None, form:list=None) -> dict:
        method = route.method
        url = route.url
        bucket = route.bucket()
        lock = self._locks.get(bucket)
        if lock is None:
            lock = asyncio.Lock()
            if bucket is not None:
                self._locks[bucket] = lock
        headers = {'User-Agent': self._user_agent,
                   'X-Ratelimit-Precision': 'millisecond',
                   'Authorization': 'Bot ' + self.token}
        content = None
        if json_data is not None:
            # unlike forms, aiohttp doesn't detect JSON, so we must set the header manually.
            headers['Content-Type'] = 'application/json'
            content = json_data
        if not self._global_over.is_set():
            # wait until the global lock is complete
            await self._global_over.wait()
        await lock.acquire()
        with _MaybeUnlock(lock) as maybe_lock:
            for tries in range(5):
                if form:
                    form_data = FormData()
                    for params in form:
                        if params['name'].startswith('file'):
                            params['value'].seek(0)
                        form_data.add_field(**params)
                    content = form_data
                try:
                    async with self._session.request(method, url, headers=headers, data=content) as r:
                        log.debug('%s %s with %s has returned %s', method, url, content, r.status)
                        text = await r.text(encoding='utf-8')
                        if r.headers.get('content-type', '') == 'application/json':
                            data = json.loads(text)
                        else:
                            # Thanks Cloudflare
                            data = {'message': text}
                        # check if we have rate limit header information
                        remaining = r.headers.get('X-Ratelimit-Remaining')
                        if remaining == '0' and r.status != 429:
                            # we've depleted our current bucket
                            reset_after = r.headers.get('X-Ratelimit-Reset-After')
                            if reset_after:
                                delta = float(reset_after)
                            else:
                                utc = datetime.timezone.utc
                                now = datetime.datetime.now(utc)
                                reset = datetime.datetime.fromtimestamp(float(r.headers['X-Ratelimit-Reset']), utc)
                                delta = (reset - now).total_seconds()
                            log.debug('A rate limit bucket has been exhausted (bucket: %s, retry: %s).', bucket, delta)
                            maybe_lock.defer()
                            self._loop.call_later(delta, lock.release)
                        # the request was successful so just return the text/json
                        if 300 > r.status >= 200:
                            log.debug('%s %s has received %s', method, url, data)
                            return data
                        # we are being rate limited
                        if r.status == 429:
                            if not r.headers.get('Via'):
                                # Banned by Cloudflare more than likely.
                                raise HTTPException(r, data)
                            # check if it's a global rate limit
                            is_global = data.get('global', False)
                            if is_global:
                                log.warning('Global rate limit has been hit.')
                                self._global_over.clear()
                            else:
                                log.warning('Bucket "%s" is being rate limited.', bucket)
                            # sleep a bit
                            retry_after = data.get('retry_after', 5000.0) / 1000.0
                            log.warning('Retrying in %.2f seconds.', retry_after)
                            await asyncio.sleep(retry_after)
                            # release the global lock now that the global rate limit has passed
                            if is_global:
                                self._global_over.set()
                            continue
                        # we've received a 500 or 502, unconditional retry
                        if r.status in {500, 502}:
                            await asyncio.sleep(1 + tries * 2)
                            continue
                        # the usual error cases
                        if r.status == 401:
                            raise Unauthorized(r, data)
                        if r.status == 403:
                            raise Forbidden(r, data)
                        elif r.status == 404:
                            raise NotFound(r, data)
                        elif r.status == 503:
                            raise DiscordServerError(r, data)
                        else:
                            raise HTTPException(r, data)
                # This is handling exceptions from the request
                except OSError as e:
                    # Connection reset by peer
                    if tries < 4 and e.errno in (54, 10054):
                        continue
                    raise
            # We've run out of retries, raise.
            if r.status >= 500:
                raise DiscordServerError(r, data)
            raise HTTPException(r, data)

    async def close(self) -> None:
        if self._session:
            await self._session.close()
