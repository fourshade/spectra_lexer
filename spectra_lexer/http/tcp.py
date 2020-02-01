""" Module for creating and listening to TCP/IP socket connections. """

from _socket import socket, SHUT_WR, SO_REUSEADDR, SOL_SOCKET, SOL_TCP, TCP_NODELAY
from io import BufferedReader, RawIOBase
from select import select
from threading import Thread
from typing import BinaryIO


class TCPConnection:
    """ Data structure for an open TCP connection (in the server role). """

    def __init__(self, stream:BinaryIO, addr:str, port:int) -> None:
        self.stream = stream  # Raw binary I/O stream.
        self.addr = addr      # Client IP address.
        self.port = port      # Client TCP port.


class TCPConnectionHandler:
    """ Interface for a handler of incoming TCP client connections. """

    def handle_connection(self, conn:TCPConnection) -> None:
        """ Handle a TCP connection for its entire duration. It will be closed when this method exits. """
        raise NotImplementedError


class _SocketReader(RawIOBase):
    """ Aliases socket reading functions to match I/O methods. """

    def __init__(self, sock:socket) -> None:
        super().__init__()
        self.readinto = sock.recv_into

    def readable(self) -> bool:
        return True


class _SocketStream(BufferedReader, BinaryIO):
    """ A raw socket connection which sends/receives data as a binary I/O stream.
        The I/O reader is line-buffered; the writer is raw. """

    def __init__(self, sock:socket) -> None:
        super().__init__(_SocketReader(sock))
        self._sock = sock

    def write(self, data:bytes) -> int:
        self._sock.sendall(data)
        return len(data)

    def writable(self) -> bool:
        return True

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

    def accept(self) -> TCPConnection:
        """ Connect to the client and return an I/O stream along with the client's IP address and TCP port. """
        fd, (addr, port) = self._accept()
        sock = socket(fileno=fd)
        stream = _SocketStream(sock)
        return TCPConnection(stream, addr, port)

    def __enter__(self) -> "TCPServerSocket":
        return self

    def __exit__(self, *args) -> None:
        self.close()


class TCPServer:
    """ Simple TCP/IP stream server using sockets.  """

    def __init__(self, handler:TCPConnectionHandler, *, timeout=0.5) -> None:
        self._handler = handler  # Handler of TCP/IP connections.
        self._timeout = timeout  # Timeout in seconds to poll for new socket connections.
        self._running = False    # State variable. When set to False, the server stops after its current polling cycle.

    def start(self, address:str, port:int) -> None:
        """ Make a server socket object bound to <address:port> which opens I/O streams for connections.
            Set options to avoid delays on small packets, then bind and activate the socket.
            Poll the socket for connections until another thread calls shutdown(). """
        if self._running:
            raise RuntimeError("Server already running.")
        self._running = True
        with TCPServerSocket() as sock:
            sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
            sock.setsockopt(SOL_TCP, TCP_NODELAY, 1)
            sock.bind((address, port))
            sock.listen()
            while self._running:
                if sock.poll(self._timeout):
                    conn = sock.accept()
                    self.connect(conn)

    def connect(self, conn:TCPConnection) -> None:
        """ Send a newly established TCP connection to the connection handler. Close it when finished. """
        with conn.stream:
            self._handler.handle_connection(conn)

    def shutdown(self) -> None:
        """ Halt serving and close any open sockets and files. Must be called by another thread. """
        self._running = False


class ThreadedTCPServer(TCPServer):
    """ Handles each connection with a new thread. The handler must be thread-safe. """

    def connect(self, *args) -> None:
        Thread(target=super().connect, args=args, daemon=True).start()
