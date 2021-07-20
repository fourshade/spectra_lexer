import asyncio
import concurrent.futures
import json
import sys
import threading
import time
import zlib

from aiohttp import ClientWebSocketResponse, WSMsgType

from .logger import log


class Intents:

    GUILDS = 1 << 0
    GUILD_MEMBERS = 1 << 1
    GUILD_BANS = 1 << 2
    GUILD_EMOJIS_AND_STICKERS = 1 << 3
    GUILD_INTEGRATIONS = 1 << 4
    GUILD_WEBHOOKS = 1 << 5
    GUILD_INVITES = 1 << 6
    GUILD_VOICE_STATES = 1 << 7
    GUILD_PRESENCES = 1 << 8
    GUILD_MESSAGES = 1 << 9
    GUILD_MESSAGE_REACTIONS = 1 << 10
    GUILD_MESSAGE_TYPING = 1 << 11
    DIRECT_MESSAGES = 1 << 12
    DIRECT_MESSAGE_REACTIONS = 1 << 13
    DIRECT_MESSAGE_TYPING = 1 << 14


class GatewayEventDispatcher:
    """ Interface for Discord gateway event dispatchers. """

    def required_intents(self) -> int:
        """ Return the OR product of every intent required to receive events of interest. """
        return 0

    def dispatch(self, event:str, data:dict) -> None:
        raise NotImplementedError


class ConnectionClosed(Exception):
    """ Exception thrown when the gateway connection is closed for reasons that could not be handled internally. """

    def __init__(self, code:int) -> None:
        self.code = code  # Close code of the websocket.
        super().__init__(f'WebSocket closed with {code}')


class ReconnectWebSocket(Exception):
    """ Signals to safely reconnect the websocket. """

    def __init__(self, *, resume=True) -> None:
        self.resume = resume
        self.op = 'RESUME' if resume else 'IDENTIFY'


class _WebSocketClosure(Exception):
    """ An exception to make up for the fact that aiohttp doesn't signal closure. """


class GatewayRatelimiter:

    def __init__(self, count=110, per=60.0) -> None:
        self.max = count  # The default is 110 to give room for at least 10 heartbeats per minute
        self.remaining = count
        self.window = 0.0
        self.per = per
        self.lock = asyncio.Lock()

    def _get_delay(self):
        current = time.time()
        if current > self.window + self.per:
            self.remaining = self.max
        if self.remaining == self.max:
            self.window = current
        if self.remaining == 0:
            return self.per - (current - self.window)
        self.remaining -= 1
        if self.remaining == 0:
            self.window = current
        return 0.0

    async def block(self) -> None:
        async with self.lock:
            delta = self._get_delay()
            if delta:
                log.warning('WebSocket is ratelimited, waiting %.2f seconds', delta)
                await asyncio.sleep(delta)


class KeepAliveHandler(threading.Thread):

    def __init__(self, ws:'GatewayWebSocket', interval:float, timeout:float) -> None:
        super().__init__()
        self.daemon = True
        self._ws = ws
        self._interval = interval
        self._timeout = timeout
        self._loop = asyncio.get_event_loop()
        self._stop_ev = threading.Event()
        self._last_ack = time.perf_counter()
        self._last_send = time.perf_counter()
        self._last_recv = time.perf_counter()

    def run(self) -> None:
        while not self._stop_ev.wait(self._interval):
            if self._last_recv + self._timeout < time.perf_counter():
                log.warning("Stopped responding to the gateway. Closing and restarting.")
                coro = self._ws.close()
                f = asyncio.run_coroutine_threadsafe(coro, loop=self._loop)
                try:
                    f.result()
                except Exception:
                    log.exception('An error occurred while stopping the gateway. Ignoring.')
                finally:
                    self.stop()
                    return
            # This bypasses the rate limit handling code since it has a higher priority
            coro = self._ws.send_heartbeat(limited=False)
            f = asyncio.run_coroutine_threadsafe(coro, loop=self._loop)
            try:
                # block until sending is complete
                total = 0
                while True:
                    try:
                        f.result(10)
                        break
                    except concurrent.futures.TimeoutError:
                        total += 10
                        log.warning(f'Heartbeat blocked for more than {total} seconds.')
            except Exception:
                self.stop()
            else:
                self._last_send = time.perf_counter()

    def stop(self) -> None:
        self._stop_ev.set()

    def tick(self) -> None:
        self._last_recv = time.perf_counter()

    def ack(self) -> None:
        self._last_ack = ack_time = time.perf_counter()
        latency = ack_time - self._last_send
        if latency > 10:
            log.warning(f"Can't keep up, websocket is {latency:.1f}s behind.")


class Opcodes:

    DISPATCH = 0               # Receive only. Denotes an event to be sent to Discord, such as READY.
    HEARTBEAT = 1              # Sent to tell Discord to keep the connection alive. Received to ask if it is.
    IDENTIFY = 2               # Send only. Starts a new session.
    PRESENCE_UPDATE = 3        # Send only. Updates your presence.
    VOICE_STATE_UPDATE = 4     # Send only. Starts a new connection to a voice guild.
    RESUME = 6                 # Send only. Resumes an existing connection.
    RECONNECT = 7              # Receive only. Tells the client to reconnect to a new gateway.
    REQUEST_GUILD_MEMBERS = 8  # Send only. Asks for the full member list of a guild.
    INVALID_SESSION = 9        # Receive only. Tells the client to optionally invalidate the session and IDENTIFY again.
    HELLO = 10                 # Receive only. Tells the client the heartbeat interval.
    HEARTBEAT_ACK = 11         # Receive only. Confirms receiving a heartbeat.
    GUILD_SYNC = 12            # Send only. Requests a guild sync.


class GatewayWebSocket:
    """ Implements a WebSocket for Discord's gateway v9. """

    def __init__(self, socket:ClientWebSocketResponse, dispatcher:GatewayEventDispatcher, *,
                 initial=False, resume=False, session=None, sequence=None, heartbeat_timeout=60.0) -> None:
        self._socket = socket
        self._dispatcher = dispatcher
        self._keep_alive = None
        self._initial_identify = initial
        self._resume = resume
        self.session_id = session
        self.sequence = sequence
        self._max_heartbeat_timeout = heartbeat_timeout
        self._zlib = zlib.decompressobj()
        self._buffer = bytearray()
        self._close_code = None
        self._rate_limiter = GatewayRatelimiter()

    def is_open(self) -> bool:
        return not self._socket.closed

    async def connect(self, token:str) -> None:
        """ Connect after polling for OP Hello. """
        await self.poll_event()
        if self._resume:
            await self._resume(token)
        else:
            await self._identify(token)

    async def _identify(self, token:str) -> None:
        """ Send the IDENTIFY packet. """
        payload = {
            'op': Opcodes.IDENTIFY,
            'd': {
                'token': token,
                'properties': {
                    '$os': sys.platform,
                    '$browser': 'aiohttp',
                    '$device': 'aiohttp'
                },
                'compress': True,
                'presence': {
                    'since': None,
                    'activities': [],
                    'status': 'online',
                    'afk': False
                },
                'intents': self._dispatcher.required_intents()
            }
        }
        if not self._initial_identify:
            await asyncio.sleep(5.0)
        await self._send_json(payload)
        log.info('Sent the IDENTIFY payload.')

    async def _resume(self, token:str) -> None:
        """ Send the RESUME packet. """
        payload = {
            'op': Opcodes.RESUME,
            'd': {
                'token': token,
                'session_id': self.session_id,
                'seq': self.sequence
            }
        }
        await self._send_json(payload)
        log.info('Sent the RESUME payload.')

    async def _received_message(self, msg) -> None:
        if type(msg) is bytes:
            # Detect and decompress zlib payloads to plaintext JSON.
            self._buffer.extend(msg)
            if len(msg) < 4 or msg[-4:] != b'\x00\x00\xff\xff':
                return
            msg = self._zlib.decompress(self._buffer)
            msg = msg.decode('utf-8')
            self._buffer = bytearray()
        log.debug('WebSocket Event: %s', msg)
        msg = json.loads(msg)
        op = msg.get('op')
        data = msg.get('d')
        seq = msg.get('s')
        if seq is not None:
            self.sequence = seq
        if self._keep_alive:
            self._keep_alive.tick()
        if op != Opcodes.DISPATCH:
            if op == Opcodes.RECONNECT:
                # "reconnect" can only be handled by the Client so we terminate our connection
                # and raise an internal exception signalling to reconnect.
                log.debug('Received RECONNECT opcode.')
                await self.close()
                raise ReconnectWebSocket()
            if op == Opcodes.HEARTBEAT_ACK:
                if self._keep_alive:
                    self._keep_alive.ack()
                return
            if op == Opcodes.HEARTBEAT:
                if self._keep_alive:
                    await self.send_heartbeat()
                return
            if op == Opcodes.HELLO:
                interval = data['heartbeat_interval'] / 1000.0
                self._keep_alive = KeepAliveHandler(self, interval, self._max_heartbeat_timeout)
                # send a heartbeat immediately
                await self.send_heartbeat()
                self._keep_alive.start()
                return
            if op == Opcodes.INVALID_SESSION:
                if data is True:
                    await self.close()
                    raise ReconnectWebSocket()
                self.sequence = None
                self.session_id = None
                log.info('Session has been invalidated.')
                await self.close(code=1000)
                raise ReconnectWebSocket(resume=False)
            log.warning('Unknown OP code %s.', op)
            return
        event = msg.get('t')
        if event == 'READY':
            self.sequence = msg['s']
            self.session_id = data['session_id']
            log.info('Connected to Gateway (Session ID: %s).', self.session_id)
        elif event == 'RESUMED':
            log.info('Successfully RESUMED session %s.', self.session_id)
        self._dispatcher.dispatch(event, data)

    def _can_handle_close(self) -> bool:
        code = self._close_code or self._socket.close_code
        return code not in (1000, 4004, 4010, 4011, 4012, 4013, 4014)

    async def poll_event(self) -> None:
        """ Poll for DISPATCH events and handle the general gateway loop. """
        try:
            msg = await self._socket.receive(timeout=self._max_heartbeat_timeout)
            if msg.type in (WSMsgType.TEXT, WSMsgType.BINARY):
                await self._received_message(msg.data)
            elif msg.type in (WSMsgType.CLOSED, WSMsgType.CLOSING, WSMsgType.CLOSE):
                log.debug('Received %s', msg)
                raise _WebSocketClosure
            elif msg.type is WSMsgType.ERROR:
                log.debug('Received %s', msg)
                raise msg.data
        except (asyncio.TimeoutError, _WebSocketClosure) as e:
            # Ensure the keep alive handler is closed
            if self._keep_alive:
                self._keep_alive.stop()
                self._keep_alive = None
            if isinstance(e, asyncio.TimeoutError):
                log.info('Timed out receiving packet. Attempting a reconnect.')
                raise ReconnectWebSocket() from None
            code = self._close_code or self._socket.close_code
            if self._can_handle_close():
                log.info('Websocket closed with %s, attempting a reconnect.', code)
                raise ReconnectWebSocket() from None
            else:
                log.info('Websocket closed with %s, cannot reconnect.', code)
                raise ConnectionClosed(code) from None

    async def _send_json(self, data:dict, *, limited=True) -> None:
        try:
            if limited:
                await self._rate_limiter.block()
            s = json.dumps(data, separators=(',', ':'), ensure_ascii=True)
            await self._socket.send_str(s)
        except RuntimeError as exc:
            if not self._can_handle_close():
                raise ConnectionClosed(self._socket.close_code) from exc

    async def send_heartbeat(self, *, limited=True) -> None:
        log.debug('Keeping websocket alive with sequence %s.', self.sequence)
        await self._send_json({'op': Opcodes.HEARTBEAT, 'd': self.sequence}, limited=limited)

    async def close(self, code=4000) -> None:
        if self._keep_alive:
            self._keep_alive.stop()
            self._keep_alive = None
        self._close_code = code
        await self._socket.close(code=code)
