""" Module for servicing HTTP connections and requests using I/O streams. """

from io import RawIOBase
import sys
from traceback import format_exc
from typing import Callable

from .request import HTTPRequest
from .response import HTTPResponse, HTTPError
from .methods import HTTPMethodHandler


class _Logger:
    """ Logger wrapper with a buffer of chained messages which are joined and logged on a direct call. """

    def __init__(self, logger:Callable[[str], None]):
        self._log = logger
        self._buffer = []

    def add(self, message:str) -> None:
        self._buffer.append(message)

    def __call__(self, message:str) -> None:
        """ Add the last message to the buffer, concatenate everything, log it, and start over. """
        self.add(message)
        self._log("".join(self._buffer))
        self._buffer = []


class HTTPDispatcher:
    """ Dispatches methods specific to HTTP requests.
        Threading is required so that one client can't hog the entire server with a persistent connection. """

    _handler: HTTPMethodHandler  # Handles all non-error HTTP methods.
    _server_version: str         # Version string sent with each response.
    _logger: Callable            # Used to log all HTTP responses and errors (but not headers).

    def __init__(self, handler:HTTPMethodHandler, server_version:str="Undefined/0.0", logger:Callable=sys.stderr.write):
        self._handler = handler
        self._server_version = server_version
        self._logger = logger

    def __call__(self, stream, addr:str) -> None:
        """ Open an HTTP connection to handle any requests. """
        def log_with_addr(msg:str) -> None:
            """ Wrap the logger to add the client address to each line. """
            self._logger(f'{addr} - {msg}')
        try:
            log_with_addr("Connection opened.")
            self.handle(stream, log_with_addr)
        except OSError:
            log_with_addr("Connection aborted by OS.")
        except Exception:
            log_with_addr(format_exc())
        finally:
            stream.close()
            log_with_addr("Connection terminated.")

    def handle(self, stream:RawIOBase, logger:Callable=sys.stderr.write) -> None:
        """ Process HTTP requests until connection close or error. """
        log = _Logger(logger)
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

    def _send(self, response:HTTPResponse, stream:RawIOBase, log:_Logger) -> None:
        """ Send an HTTP response with the current date and server software version and log the status line. """
        status = response.send(stream, date=True, server=self._server_version)
        log(status)
