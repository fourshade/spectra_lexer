import asyncio
import signal

from aiohttp import ClientError

from .backoff import ExponentialBackoff
from .event import EventHandler
from .gateway import ConnectionClosed, GatewayEventDispatcher, GatewayWebSocket, ReconnectWebSocket
from .http import HTTPClient, HTTPException, Unauthorized, NotFound
from .request import BotGatewayRequest, GatewayRequest
from .logger import log


class ClientException(Exception):
    """ Exception that's thrown when an operation in the Client fails.
        These are usually for exceptions that happened due to user input. """


async def _run_event(coro, event:str, data:dict) -> None:
    try:
        await coro(data)
    except asyncio.CancelledError:
        pass
    except Exception:
        log.exception("Ignoring exception in " + event)


class Client(GatewayEventDispatcher):
    """ This class is used to interact with the Discord WebSocket and API as a client. """

    def __init__(self, http:HTTPClient, token:str, *, is_bot=True) -> None:
        self._http = http
        self._token = token  # Raw authentication token.
        self._is_bot = is_bot
        self._ws = None  # The websocket gateway the client is currently connected to.
        self._event_handlers = []
        self._loop = asyncio.get_event_loop()
        self._closed = False

    def required_intents(self) -> int:
        intents = 0
        for handler in self._event_handlers:
            intents |= handler.required_intents()
        return intents

    def dispatch(self, event:str, data:dict) -> None:
        for handler in self._event_handlers:
            coro = getattr(handler, 'on_' + event.lower(), None)
            if coro is not None:
                wrapped = _run_event(coro, event, data)
                # Schedules the task
                asyncio.Task(wrapped, loop=self._loop)

    def add_event_handler(self, handler:EventHandler) -> None:
        self._event_handlers.append(handler)

    async def close(self) -> None:
        """ Closes the connection to Discord. """
        if self._closed:
            return
        await self._http.close()
        self._closed = True
        if self._ws is not None and self._ws.is_open():
            await self._ws.close(code=1000)

    async def _get_gateway_url(self, *, encoding='json', v=9, zlib=True) -> str:
        req = BotGatewayRequest() if self._is_bot else GatewayRequest()
        data = await self._http.request(req)
        value = '{0}?encoding={1}&v={2}'
        if zlib:
            value += '&compress=zlib-stream'
        return value.format(data['url'], encoding, v)

    async def _login(self, ws_params:dict) -> None:
        """ Log in the client with the saved credentials. """
        log.info('Connecting to Discord...')
        try:
            gateway_url = await self._get_gateway_url()
        except Unauthorized as exc:
            raise ClientException('Improper token has been passed.') from exc
        except NotFound as exc:
            raise ClientException('The gateway to connect to Discord was not found.') from exc
        socket = await self._http.ws_connect(gateway_url)
        self._ws = GatewayWebSocket(socket, self, **ws_params)
        log.info(f'Created websocket connected to {gateway_url}.')
        await self._ws.connect(self._token)

    async def connect(self, *, reconnect=True) -> None:
        """ Create a websocket connection to listen to messages from Discord.
            This is a loop that runs the entire event system.
            Control is not resumed until the WebSocket connection is terminated.
            reconnect: If True, attempt reconnecting after most failures. """
        backoff = ExponentialBackoff()
        ws_params = {'initial': True}
        while not self._closed:
            try:
                coro = self._login(ws_params)
                await asyncio.wait_for(coro, timeout=60.0)
                ws_params['initial'] = False
                while True:
                    await self._ws.poll_event()
            except ReconnectWebSocket as e:
                log.info('Got a request to %s the websocket.', e.op)
                log.info("Disconnected from websocket.")
                ws_params.update(sequence=self._ws.sequence, resume=e.resume, session=self._ws.session_id)
                continue
            except (OSError,
                    HTTPException,
                    ConnectionClosed,
                    ClientError,
                    asyncio.TimeoutError) as exc:
                log.info("Disconnected from websocket.")
                if not reconnect:
                    await self.close()
                    if isinstance(exc, ConnectionClosed) and exc.code == 1000:
                        # clean close, don't re-raise this
                        return
                    raise
                if self._closed:
                    return
                # If we get connection reset by peer then try to RESUME
                if isinstance(exc, OSError) and exc.errno in (54, 10054):
                    ws_params.update(initial=False, resume=True,
                                     sequence=self._ws.sequence, session=self._ws.session_id)
                    continue
                # We should only get this when an unhandled close code happens,
                # such as a clean disconnect (1000) or a bad state (bad token, no sharding, etc)
                # sometimes, discord sends us 1000 for unknown reasons so we should reconnect
                # regardless and rely on is_closed instead
                if isinstance(exc, ConnectionClosed):
                    if exc.code == 4014:
                        msg = 'Client requested privileged intents that are not enabled in the developer portal.'
                        raise ClientException(msg) from None
                    if exc.code != 1000:
                        await self.close()
                        raise
                retry = backoff.delay()
                log.exception(f"Attempting a reconnect in {retry:.2f}s")
                await asyncio.sleep(retry)
                # Always try to RESUME the connection.
                # If the connection is not RESUME-able then the gateway will invalidate the session.
                # This is apparently what the official Discord client does.
                ws_params.update(sequence=self._ws.sequence, resume=True, session=self._ws.session_id)

    async def _run(self, **kwargs) -> None:
        try:
            await self.connect(**kwargs)
        finally:
            if not self._closed:
                await self.close()

    def run(self, **kwargs) -> None:
        """ A blocking call that abstracts away the event loop initialization.
            This function must be the last function to call due to the fact that it
            is blocking. That means that registration of events or anything being
            called after this function call will not execute until it returns. """
        loop = self._loop
        try:
            loop.add_signal_handler(signal.SIGINT, lambda: loop.stop())
            loop.add_signal_handler(signal.SIGTERM, lambda: loop.stop())
        except NotImplementedError:
            pass
        def stop_loop_on_completion(_) -> None:
            loop.stop()
        coro = self._run(**kwargs)
        future = asyncio.ensure_future(coro, loop=loop)
        future.add_done_callback(stop_loop_on_completion)
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            log.info('Received signal to terminate application and event loop.')
        except Exception:
            log.exception('CLIENT EXCEPTION')
        finally:
            future.remove_done_callback(stop_loop_on_completion)
            log.info('Cleaning up tasks.')
            self._cleanup_loop()

    def _cancel_tasks(self) -> None:
        loop = self._loop
        try:
            task_retriever = asyncio.Task.all_tasks
        except AttributeError:
            # future proofing for 3.9.
            task_retriever = asyncio.all_tasks
        tasks = {t for t in task_retriever(loop=loop) if not t.done()}
        if not tasks:
            return
        log.info('Cleaning up after %d tasks.', len(tasks))
        for task in tasks:
            task.cancel()
        loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
        log.info('All tasks finished cancelling.')
        for task in tasks:
            if task.cancelled():
                continue
            if task.exception() is not None:
                loop.call_exception_handler({
                    'message': 'Unhandled exception during Client.run shutdown.',
                    'exception': task.exception(),
                    'task': task
                })

    def _cleanup_loop(self) -> None:
        loop = self._loop
        try:
            self._cancel_tasks()
            loop.run_until_complete(loop.shutdown_asyncgens())
        finally:
            log.info('Closing the event loop.')
            loop.close()
