from functools import partial
from http import HTTPStatus
from http.server import HTTPServer, SimpleHTTPRequestHandler
import sys
from typing import Callable


class SpectraRequestHandler(SimpleHTTPRequestHandler):

    protocol_version = "HTTP/1.1"  # HTTP 1.1 is required for persistent connections.
    server_version = "Spectra/0.1"

    _process: Callable[[bytes, Callable], None]  # Main callback to process user state.
    _logger: Callable[[str], None]               # Callback to write request formatted log strings.

    def __init__(self, *args, callback:Callable, logger:Callable=sys.stderr.write, **kwargs):
        self._process = callback
        self._logger = logger
        super().__init__(*args, **kwargs)

    def do_POST(self) -> None:
        """ Start service of a POST request. """
        data = self._receive_data()
        self._process(data, self.finish_POST)

    def finish_POST(self, response:bytes) -> None:
        """ Finish the request by sending the processed data. """
        self.send_response(HTTPStatus.OK)
        self._send_data(response, "application/json")

    def _receive_data(self) -> bytes:
        """ Return any request content data as a bytes object. """
        size = int(self.headers["Content-Length"])
        data = self.rfile.read(size)
        return data

    def _send_data(self, response:bytes, ctype:str="text/html") -> None:
        """ Write the response headers and data for content with MIME type <ctype>. """
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, fmt_string:str, *args) -> None:
        """ Log an arbitrary message using the log callback given at instantiation. """
        self._logger(f'{self.address_string()} [{self.log_date_time_string()}] {fmt_string % args}\n')


class SpectraHTTPServer(HTTPServer):

    def __init__(self, server_address:tuple, **kwargs):
        """ Add the given kwargs to every instantiated handler. """
        handler_cls_with_data = partial(SpectraRequestHandler, **kwargs)
        super().__init__(server_address, handler_cls_with_data)
