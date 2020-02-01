""" Module for servicing HTTP connections and requests using I/O streams. """

import sys

from traceback import format_exc
from typing import Callable, Iterator

from .request import HTTPRequestReader
from .response import HTTPResponseWriter
from .status import HTTPError
from .service import HTTPRequestHandler
from .tcp import TCPConnection, TCPConnectionHandler


class HTTPConnectionHandler(TCPConnectionHandler):
    """ Handles TCP connections by dispatching HTTP requests to a request handler.
        Threading is required to prevent one client from hogging the entire server with a persistent connection.
        To that end, this class is thread-safe to the extent that the request handler and logger are. """

    SERVER_VERSION = f"Spectra/0.5 Python/{sys.version.split()[0]}"

    def __init__(self, req_handler:HTTPRequestHandler, log:Callable[[str], None]=print) -> None:
        self._req_handler = req_handler  # Handler for all HTTP requests. May delegate to subhandlers.
        self._log = log                  # Callable used to log all HTTP responses and errors (but not headers).

    def handle_connection(self, conn:TCPConnection) -> None:
        """ Process all HTTP requests on an open TCP connection. Log all results with the client address and port. """
        log_header = conn.client_info() + ' - '
        def log(message:str) -> None:
            self._log(log_header + message)
        try:
            log("Connection opened.")
            reader = HTTPRequestReader(conn)
            writer = HTTPResponseWriter(conn, self.SERVER_VERSION)
            for s in self._process(reader, writer):
                log(s)
        except OSError:
            log("Connection aborted by OS.")
        except Exception:
            log('EXCEPTION\n' + format_exc())
        finally:
            log("Connection terminated.")

    def _process(self, reader:HTTPRequestReader, writer:HTTPResponseWriter) -> Iterator[str]:
        """ Process requests and yield log messages until connection close or error. """
        request = None
        try:
            while True:
                request = reader.read()
                if request is None:
                    return
                # Examine the headers and look for continue directives first.
                headers = request.headers
                if headers.expect_continue():
                    status = writer.write_continue()
                    yield f"{request} -> {status}"
                # Call the request handler and yield its result.
                response = self._req_handler(request)
                status = writer.write(response)
                yield f"{request} -> {status}"
                if not headers.keep_alive():
                    return
        except HTTPError as e:
            status = writer.write_error(e)
            yield f"{request} -> {status}"
        except Exception:
            # For non-HTTP exceptions, send an internal error response and raise to log the traceback.
            e = HTTPError.INTERNAL_SERVER_ERROR()
            writer.write_error(e)
            raise
