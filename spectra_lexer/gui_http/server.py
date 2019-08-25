from collections import Callable
import sys
from threading import Lock, Thread

from .dispatch import HTTPDispatcher
from .methods import HTTPFileGetter, HTTPMethodTable, HTTPJSONProcessor
from .tcp import TCPServerSocket


class SpectraJSONProcessor(HTTPJSONProcessor):

    def _process(self, state:dict, path:str, *args) -> dict:
        """ The decoded object is the state dict, and the relative path includes the action. """
        action = path.split('/')[-1]
        return self._processor(state, action)

    def _dumps(self, changed_state:dict) -> bytes:
        """ Keep Unicode characters intact. Make sure bytes objects are converted to normal strings. """
        return super()._dumps(changed_state, ensure_ascii=False, default=bytes.decode)


class LockingCallable:
    """ Wraps a callable to lock it for a single thread's use. Not re-entrant. """

    def __init__(self, func:Callable):
        self._lock = Lock()
        self._func = func

    def __call__(self, *args, **kwargs):
        with self._lock:
            return self._func(*args, **kwargs)


class HTTPServer:
    """ Class for socket-based TCP/IP stream server, JSON, and communication with the view layer. """

    SERVER_VERSION = f"Spectra/0.1 Python/{sys.version.split()[0]}"

    _dispatcher: HTTPDispatcher  # Handles each HTTP method independently.
    _running: bool = False

    def __init__(self, directory:str, processor:Callable, logger:Callable):
        """ Outside code may not be thread-safe. Make sure to log or process only one response at a time. """
        processor = LockingCallable(processor)
        logger = LockingCallable(logger)
        method_handler = HTTPMethodTable(GET=HTTPFileGetter(directory),
                                         HEAD=HTTPFileGetter(directory, head=True),
                                         POST=SpectraJSONProcessor(processor))
        self._dispatcher = HTTPDispatcher(method_handler, self.SERVER_VERSION, logger)

    def start(self, *args) -> None:
        """ Start the server and poll for connections on a new thread. """
        if self._running:
            raise RuntimeError("HTTP server already running.")
        Thread(target=self._serve_forever, args=args, daemon=True).start()

    def _serve_forever(self, address:str, port:int) -> None:
        """ Make a server socket object which creates other sockets for connections and poll it periodically. """
        self._running = True
        with TCPServerSocket(address, port) as sock:
            while self._running:
                if sock.poll():
                    # Handle each connection with a new thread.
                    Thread(target=self._dispatcher, args=sock.accept(), daemon=True).start()

    def shutdown(self) -> None:
        """ Halt serving and close any open sockets and files. Must be called by another thread. """
        self._running = False
