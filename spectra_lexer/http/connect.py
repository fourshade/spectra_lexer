""" Module for servicing HTTP connections and requests using I/O streams. """

from traceback import format_exc
from typing import BinaryIO, Iterator, Optional

from .request import HTTPRequest, HTTPRequestReader
from .response import HTTPResponse, HTTPResponseHeaders, HTTPResponseWriter
from .status import HTTPError
from .service import HTTPRequestHandler
from .tcp import LineLogger, TCPConnectionHandler


class HTTPConnectionHandler(TCPConnectionHandler):
    """ Handles TCP connections by dispatching HTTP requests to a request handler.
        Threading is required to prevent one client from hogging the entire server with a persistent connection.
        To that end, this class is thread-safe to the extent that the request handler and logger are. """

    def __init__(self, req_handler:HTTPRequestHandler, *, server_version:str=None) -> None:
        self._req_handler = req_handler        # Handler for all HTTP requests. May delegate to subhandlers.
        self._server_version = server_version  # Optional server version string sent with each response.

    def handle_connection(self, stream:BinaryIO, log:LineLogger) -> None:
        """ Process all HTTP requests on an open TCP stream and write log messages until close. """
        try:
            log("Connection opened.")
            for s in self._process(stream):
                log(s)
            log("Connection terminated.")
        except OSError:
            log("Connection aborted by OS.")
        except HTTPError:
            log("Connection terminated by error.")
        except Exception:
            log('Connection terminated with exception:')
            log(format_exc())

    def _process(self, stream:BinaryIO) -> Iterator[str]:
        """ Process requests and yield log messages until connection close or error. """
        reader = HTTPRequestReader(stream)
        writer = HTTPResponseWriter(stream)
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
        return self._send(request, response, writer)

    def _handle_continue(self, request:HTTPRequest, writer:HTTPResponseWriter) -> str:
        """ Write a continue response. This cannot have a message body. """
        headers = HTTPResponseHeaders()
        response = HTTPResponse.CONTINUE(headers)
        return self._send(request, response, writer)

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
        return self._send(request, response, writer)

    def _send(self, request:Optional[HTTPRequest], response:HTTPResponse, writer:HTTPResponseWriter) -> str:
        """ Add server-specific headers to a response and write it.
            Return a summary of the transaction for the log. """
        headers = response.headers
        headers.set_date()
        if self._server_version is not None:
            headers.set_server(self._server_version)
        writer.write(response)
        if request is None:
            return f'BAD REQUEST -> {response.status}'
        return f'{request.method} {request.uri.path} -> {response.status}'
