""" Module for creating and listening to TCP/IP socket connections. """

import _socket
from io import BufferedReader, RawIOBase
import select
from typing import Tuple


class _SocketReader(RawIOBase):

    def __init__(self, sock:_socket.socket):
        super().__init__()
        self.readinto = sock.recv_into

    def readable(self):
        return True


class TCPSocketIO(BufferedReader):

    def __init__(self, sock:_socket.socket):
        super().__init__(_SocketReader(sock))
        self._sock = sock

    def write(self, data):
        self._sock.sendall(data)
        return len(data)

    def writable(self):
        return True

    def fileno(self):
        return self._sock.fileno()

    def close(self):
        super().close()
        try:
            self._sock.shutdown(_socket.SHUT_WR)
        except OSError:
            pass
        self._sock.close()


class TCPServerSocket(_socket.socket):
    """ TCP socket subclass to poll for and accept connections using a basic selector. """

    def __init__(self, address:str, port:int, backlog:int=10):
        """ Bind and activate the TCP/IP socket. """
        super().__init__()
        self.setsockopt(_socket.SOL_SOCKET, _socket.SO_REUSEADDR, 1)
        self.bind((address, port))
        self.listen(backlog)

    def poll(self, timeout:float) -> bool:
        """ Wait for <timeout> seconds and return True if a connection becomes ready for acceptance. """
        try:
            return bool(select.select([self.fileno()], [], [], timeout)[0])
        except (InterruptedError, OSError):
            return False

    def accept(self) -> Tuple[TCPSocketIO, str]:
        """ Connect to the client and return an I/O stream along with the client's IP address and port. """
        fd, (addr, port) = self._accept()
        sock = _socket.socket(fileno=fd)
        stream = TCPSocketIO(sock)
        return stream, f'{addr}:{port}'

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        self.close()


class BaseTCPServer:
    """ Abstract base class for a simple TCP/IP stream server using sockets. Just implement __call__. """

    _running: bool = False

    def start(self, address:str, port:int, timeout:float=0.5) -> None:
        """ Make a server socket object which creates other sockets for connections and poll it periodically. """
        if self._running:
            raise RuntimeError("Server already running.")
        self._running = True
        with TCPServerSocket(address, port) as sock:
            while self._running:
                if sock.poll(timeout):
                    self(*sock.accept())

    def __call__(self, stream:RawIOBase, addr:str) -> None:
        """ A raw TCP connection provides an I/O stream to send/receive data and an address information string. """
        raise NotImplementedError

    def shutdown(self) -> None:
        """ Halt serving and close any open sockets and files. Must be called by another thread. """
        self._running = False
