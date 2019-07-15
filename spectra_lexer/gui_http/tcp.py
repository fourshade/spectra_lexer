""" Module for creating and listening to TCP/IP socket connections. """

import _socket
from io import BufferedReader, RawIOBase
import select


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

    def poll(self, timeout:float=0.5) -> bool:
        """ Return True if a connection is ready for acceptance. """
        try:
            return bool(select.select([self.fileno()], [], [], timeout)[0])
        except (InterruptedError, OSError):
            return False

    def accept(self) -> tuple:
        """ Connect to the client and return an I/O stream to send/receive data and an address information string. """
        fd, (addr, port) = self._accept()
        sock = _socket.socket(fileno=fd)
        stream = TCPSocketIO(sock)
        return stream, f'{addr}:{port}'

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        self.close()
