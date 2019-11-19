""" Module for servicing HTTP connections and requests using I/O streams. """

from io import RawIOBase
import sys
from threading import Thread
from traceback import format_exc
from typing import Callable, Iterable, Iterator, Tuple

from .methods import HTTPRequestHandler
from .request import HTTPRequest, HTTPRequestParser
from .response import HTTPResponse, HTTPError
from .tcp import BaseTCPServer


class HTTPServer(BaseTCPServer):
    """ Handles HTTP connections and dispatches HTTP requests to a specific handler.
        Threading is required to prevent one client from hogging the entire server with a persistent connection.
        To that end, this class is thread-safe to the extent that the request handler and logger are. """

    server_version = f"Spectra/0.3 Python/{sys.version.split()[0]}"  # Server version string sent with each response.

    def __init__(self, req_handler:HTTPRequestHandler, log:Callable[[str], None]=print, *, threaded=False) -> None:
        self._req_handler = req_handler  # Handler for all HTTP requests. May delegate to subhandlers.
        self._log = log                  # Callable used to log all HTTP responses and errors (but not headers).
        self._threaded = threaded        # If True, handle each connection with a new thread.

    def connect(self, *args) -> None:
        if self._threaded:
            Thread(target=self._connect, args=args, daemon=True).start()
        else:
            self._connect(*args)

    def _connect(self, stream:RawIOBase, addr:str) -> None:
        """ Process all requests on an open HTTP connection. Log all results with the client address. """
        def log(message:str) -> None:
            self._log(f'{addr} - {message}')
        try:
            log("Connection opened.")
            parser = HTTPRequestParser(stream)
            req_iter = iter(parser.read, None)
            for request, response in self._iter_results(req_iter):
                # Send each HTTP response with the current date and server software version and log the status line.
                log(f"{request} -> {response}")
                response.update(date=True, server=self.server_version)
                response.send(stream)
        except OSError:
            log("Connection aborted by OS.")
        except Exception:
            log('HTTP EXCEPTION\n' + format_exc())
        finally:
            stream.close()
            log("Connection terminated.")

    def _iter_results(self, req_iter:Iterable[HTTPRequest]) -> Iterator[Tuple[HTTPRequest, HTTPResponse]]:
        """ Yield request/response pairs until connection close or error. """
        request = None
        try:
            for request in req_iter:
                # Examine the headers and look for continue directives first.
                headers = request.headers
                if headers.expect_continue():
                    # Yield a continue response. This cannot have a message body.
                    yield request, HTTPResponse.CONTINUE()
                # Call the request handler and yield its result.
                response = self._req_handler(request)
                yield request, response
                if not headers.keep_alive():
                    return
        except HTTPError as e:
            yield request, e.response()
