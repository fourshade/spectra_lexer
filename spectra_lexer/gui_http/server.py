import selectors
import socket
from threading import Thread
from typing import Callable

from .base import GUIHTTP
from .http import SpectraHttpConnection
from spectra_lexer.system import CmdlineOption


class TCPLogger:
    """ Logger wrapper that adds client info and filters identical messages. """

    log: Callable[[str], None]
    address: str
    port: int
    last_message: str = ""

    def __init__(self, logger:Callable[[str], None], address:str, port:int):
        self.log = logger
        self.address = address
        self.port = port

    def __call__(self, message:str) -> None:
        if message != self.last_message:
            self.last_message = message
        else:
            message = "*"
        self.log(f'{self.address} - {message}')


class TCPServerSocket(socket.socket):
    """ TCP socket subclass to automatically poll for and accept connections using a generator. """

    REQUEST_QUEUE_SIZE = 10  # Maximum allowed requests in the queue before dropping any.
    POLL_INTERVAL = 0.5      # Poll for shutdown every <POLL_INTERVAL> seconds.

    def __init__(self, address:str, port:int):
        """ Bind and activate the TCP/IP socket. """
        super().__init__()
        self.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.bind((address, port))
        self.listen(self.REQUEST_QUEUE_SIZE)

    def __iter__(self):
        """ Listen for and yield one request at a time until close. """
        selector = selectors.SelectSelector()
        selector.register(self, selectors.EVENT_READ)
        with self, selector:
            while not self._closed:
                if selector.select(self.POLL_INTERVAL):
                    try:
                        yield self.accept()
                    except OSError:
                        pass


class HttpServer(GUIHTTP):
    """ Class for socket-based synchronous TCP/IP stream server. """

    address: str = CmdlineOption("http-addr", default="localhost", desc="IP address or hostname for server.")
    port: int = CmdlineOption("http-port", default=80, desc="TCP port to listen for connections.")

    sock: TCPServerSocket = None

    def GUIHTTPServe(self) -> None:
        """ Handle each request by instantiating a connection and calling it with a new thread. """
        handler_kwargs = dict(process_action=self.GUIHTTPAction, directory=self.HTTP_PUBLIC)
        Thread(target=self.repl, daemon=True).start()
        self.sock = TCPServerSocket(self.address, self.port)
        for request, addr in self.sock:
            logger = TCPLogger(self.SYSStatus, *addr)
            connection = SpectraHttpConnection(request, logger=logger, **handler_kwargs)
            Thread(target=connection, daemon=True).start()

    def repl(self) -> None:
        """ Open the console with stdin on a new thread. """
        self.SYSConsoleOpen()
        while True:
            text = input()
            if text.startswith("exit()"):
                break
            self.SYSConsoleInput(text)
        self.shutdown()

    def shutdown(self) -> None:
        """ Shut down the HTTP server. Threads with outstanding requests will finish them. """
        self.sock.close()
