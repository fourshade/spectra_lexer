""" Module for servicing HTTP connections and requests using I/O streams. """

from io import RawIOBase
from traceback import format_exc
from typing import Callable

from .request import HTTPRequest
from .response import HTTPResponse, HTTPError
from .methods import HTTPMethodHandler


class _ResponseLogger:
    """ HTTP logger wrapper with a buffer of chained messages which are joined and logged on a direct call. """

    _log: Callable[[str], None]
    _buffer: list

    def __init__(self, logger:Callable[[str], None], addr:str):
        """ Start the buffer with the client address on each line. """
        self._log = logger
        self._buffer = [addr, " - "]

    def add(self, message:str) -> None:
        self._buffer.append(message)

    def __call__(self, message:str) -> None:
        """ Add the last message to the buffer, concatenate everything, log it, and start over. """
        self.add(message)
        self._log("".join(self._buffer))
        del self._buffer[2:]


class HTTPDispatcher:
    """ Handles HTTP connections and dispatches methods specific to HTTP requests.
        Threading is required to prevent one client from hogging the entire server with a persistent connection.
        To that end, this class is thread-safe to the extent that the handler and logger are. """

    _handler: HTTPMethodHandler     # Handles all non-error HTTP methods.
    _server_version: str            # Version string sent with each response.
    _logger: Callable[[str], None]  # Used to log all HTTP responses and errors (but not headers).

    def __init__(self, handler:HTTPMethodHandler, server_version:str="Undefined/0.0", logger:Callable=print):
        self._handler = handler
        self._server_version = server_version
        self._logger = logger

    def __call__(self, stream:RawIOBase, addr:str) -> None:
        """ Handle and log all requests on an open HTTP connection. """
        log = _ResponseLogger(self._logger, addr)
        try:
            log("Connection opened.")
            self._handle(stream, log)
        except OSError:
            log("Connection aborted by OS.")
        except Exception:
            log(format_exc())
        finally:
            stream.close()
            log("Connection terminated.")

    def _handle(self, stream:RawIOBase, log:_ResponseLogger) -> None:
        """ Process HTTP requests until connection close or error. """
        try:
            while True:
                request = HTTPRequest(stream)
                if not request.method:
                    return
                log.add(f"{request} -> ")
                # Examine the headers and look for continue directives first.
                if request.expect_continue():
                    # Send a continue response. This cannot have a message body.
                    self._send(HTTPResponse.CONTINUE(), stream, log)
                # Call the method handler and send its result.
                response = self._handler(request)
                self._send(response, stream, log)
                if not request.keep_alive():
                    return
        except HTTPError as e:
            self._send(e.response, stream, log)

    def _send(self, response:HTTPResponse, stream:RawIOBase, log:_ResponseLogger) -> None:
        """ Send an HTTP response with the current date and server software version and log the status line. """
        status = response.send(stream, date=True, server=self._server_version)
        log(status)
