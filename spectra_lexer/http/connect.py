""" Module for servicing HTTP connections and requests using I/O streams. """

import sys

from traceback import format_exc
from typing import Callable, Iterator, Optional

from .request import HTTPRequest, HTTPRequestReader
from .response import HTTPResponse, HTTPResponseHeaders, HTTPResponseWriter
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
        log_header = f'{conn.addr}:{conn.port} - '
        def log(message:str) -> None:
            self._log(log_header + message)
        try:
            log("Connection opened.")
            reader = HTTPRequestReader(conn.stream)
            writer = HTTPResponseWriter(conn.stream, self.SERVER_VERSION)
            for s in self._process(reader, writer):
                log(s)
            log("Connection terminated.")
        except OSError:
            log("Connection aborted by OS.")
        except HTTPError:
            log("Connection terminated by error.")
        except Exception:
            log('Connection terminated with exception:\n' + format_exc())

    def _process(self, reader:HTTPRequestReader, writer:HTTPResponseWriter) -> Iterator[str]:
        """ Process requests and yield log messages until connection close or error. """
        while True:
            request = None
            try:
                request = reader.read()
                if request is None:
                    return
                # Examine the headers and look for continue directives first.
                headers = request.headers
                if headers.expect_continue():
                    yield self._handle_continue(request, writer)
                yield self._handle_request(request, writer)
                if not headers.keep_alive():
                    return
            except HTTPError as e:
                yield self._handle_error(request, writer, e)
                raise
            except Exception:
                # For non-HTTP exceptions, send an internal error response and reraise to log the traceback.
                e = HTTPError.INTERNAL_SERVER_ERROR()
                yield self._handle_error(request, writer, e)
                raise

    def _handle_request(self, request:HTTPRequest, writer:HTTPResponseWriter) -> str:
        """ Call the request handler and write its result. """
        response = self._req_handler(request)
        writer.write(response)
        return self._log_str(request, response)

    def _handle_continue(self, request:Optional[HTTPRequest], writer:HTTPResponseWriter) -> str:
        """ Write a continue response. This cannot have a message body. """
        headers = HTTPResponseHeaders()
        response = HTTPResponse.CONTINUE(headers)
        writer.write(response)
        return self._log_str(request, response)

    def _handle_error(self, request:Optional[HTTPRequest], writer:HTTPResponseWriter, e:HTTPError) -> str:
        """ Write an error response. This closes the connection. """
        status = e.status
        headers = HTTPResponseHeaders()
        headers.set_connection_close()
        content = b''
        if status.has_body():
            html_text = status.error_html(*e.args)
            content = html_text.encode('utf-8', 'replace')
            headers.set_content_type('text/html')
            headers.set_content_length(len(content))
        response = HTTPResponse(status, headers, content)
        writer.write(response)
        return self._log_str(request, response)

    @staticmethod
    def _log_str(request:Optional[HTTPRequest], response:HTTPResponse) -> str:
        """ Return a summary of an HTML transaction for the log. """
        if request is None:
            return f'BAD REQUEST -> {response.status}'
        return f'{request.method} {request.uri.path} -> {response.status}'
