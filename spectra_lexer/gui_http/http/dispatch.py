""" Module for servicing HTTP connections and requests using I/O streams. """

from io import RawIOBase
from traceback import format_exc
from typing import Callable

from .request import HTTPRequestParser
from .response import HTTPResponse, HTTPError
from .methods import HTTPRequestHandler


class _ResponseLogger:
    """ HTTP logger wrapper with a buffer of chained messages which are joined and logged on a direct call. """

    def __init__(self, logger:Callable[[str], None], header:str=""):
        """ Start the buffer with the header on each line. """
        self._logger = logger
        self._buffer = [header]

    def add(self, message:str) -> None:
        self._buffer.append(message)

    def __call__(self, message:str) -> None:
        """ Add the last message to the buffer, concatenate everything, log it, and start over. """
        self.add(message)
        self._logger("".join(self._buffer))
        del self._buffer[1:]


class HTTPDispatcher:
    """ Handles HTTP connections and dispatches HTTP requests to a specific handler.
        Threading is required to prevent one client from hogging the entire server with a persistent connection.
        To that end, this class is thread-safe to the extent that the handler and logger are. """

    def __init__(self, handler:HTTPRequestHandler, server_version:str= "Undefined/0.0",
                 logger:Callable[[str],None]=print):
        self._handler = handler        # Handles all non-error HTTP methods.
        self._server = server_version  # Server version string sent with each response.
        self._logger = logger          # Used to log all HTTP responses and errors (but not headers).

    def __call__(self, stream:RawIOBase, addr:str) -> None:
        """ Handle all requests on an open HTTP connection and log the results with the client address. """
        log = _ResponseLogger(self._logger, f'{addr} - ')
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
        parser = HTTPRequestParser(stream)
        try:
            while True:
                request = parser.read()
                if request is None:
                    return
                log.add(f"{request} -> ")
                # Examine the headers and look for continue directives first.
                headers = request.headers
                if headers.expect_continue():
                    # Send a continue response. This cannot have a message body.
                    self._send(HTTPResponse.CONTINUE(), stream, log)
                # Call the request handler and send its result.
                response = self._handler(request)
                self._send(response, stream, log)
                if not headers.keep_alive():
                    return
        except HTTPError as e:
            self._send(e.response(), stream, log)

    def _send(self, response:HTTPResponse, stream:RawIOBase, log:_ResponseLogger) -> None:
        """ Send an HTTP response with the current date and server software version and log the status line. """
        response.update(date=True, server=self._server)
        response.send(stream)
        log(str(response))
