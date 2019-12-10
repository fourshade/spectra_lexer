""" Module for creating and listening to TCP/IP socket connections. """

from _socket import socket, SHUT_WR, SO_REUSEADDR, SOL_SOCKET, SOL_TCP, TCP_NODELAY
from io import BufferedReader, RawIOBase
from select import select
from typing import BinaryIO, Tuple


class _SocketReader(RawIOBase):
    """ Aliases socket reading functions to match I/O methods. """

    def __init__(self, sock:socket) -> None:
        super().__init__()
        self.readinto = sock.recv_into

    def readable(self) -> bool:
        return True


class TCPSocketIO(BufferedReader):
    """ Wrapper for a binary TCP I/O socket. The reader is line-buffered; the writer is raw. """

    def __init__(self, sock:socket) -> None:
        super().__init__(_SocketReader(sock))
        self._sock = sock

    def write(self, data:bytes) -> int:
        self._sock.sendall(data)
        return len(data)

    def writable(self) -> bool:
        return True

    def fileno(self) -> int:
        return self._sock.fileno()

    def close(self) -> None:
        super().close()
        try:
            self._sock.shutdown(SHUT_WR)
        except OSError:
            pass
        self._sock.close()


class TCPServerSocket(socket):
    """ TCP socket subclass to poll for and accept connections using a basic selector. """

    def poll(self, timeout:float) -> bool:
        """ Wait for <timeout> seconds and return True if a connection becomes ready for acceptance. """
        try:
            return bool(select([self.fileno()], [], [], timeout)[0])
        except (InterruptedError, OSError):
            return False

    def accept(self) -> Tuple[TCPSocketIO, str]:
        """ Connect to the client and return an I/O stream along with the client's IP address and port. """
        fd, (addr, port) = self._accept()
        sock = socket(fileno=fd)
        stream = TCPSocketIO(sock)
        return stream, f'{addr}:{port}'

    def __enter__(self) -> "TCPServerSocket":
        return self

    def __exit__(self, *args) -> None:
        self.close()


class BaseTCPServer:
    """ Abstract base class for a simple TCP/IP stream server using sockets. Just implement connect(). """

    _running: bool = False  # State variable. When set to False, the server stops after its current polling cycle.

    def start(self, address:str, port:int, *, timeout=0.5) -> None:
        """ Make a server socket object bound to <address:port> which opens I/O streams for connections.
            Set options to avoid delays on small packets, then bind and activate the socket.
            Poll it every <timeout> seconds until another thread calls shutdown(). """
        if self._running:
            raise RuntimeError("Server already running.")
        self._running = True
        with TCPServerSocket() as sock:
            sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
            sock.setsockopt(SOL_TCP, TCP_NODELAY, 1)
            sock.bind((address, port))
            sock.listen()
            while self._running:
                if sock.poll(timeout):
                    args = sock.accept()
                    self.connect(*args)

    def connect(self, stream:BinaryIO, addr:str) -> None:
        """ Handle a TCP connection for its entire duration. Make sure to close() the stream when finished.
            A raw TCP connection provides an I/O stream to send/receive data and an address information string. """
        raise NotImplementedError

    def shutdown(self) -> None:
        """ Halt serving and close any open sockets and files. Must be called by another thread. """
        self._running = False
