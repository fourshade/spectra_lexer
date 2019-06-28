from functools import partial
from http import HTTPStatus
from http.server import HTTPServer, SimpleHTTPRequestHandler
from typing import Callable

from .base import GUIHTTP
from spectra_lexer.view import ViewState, VIEW


class SpectraRequestHandler(SimpleHTTPRequestHandler):

    protocol_version = "HTTP/1.1"
    server_version = "Spectra/0.1"

    _callback: Callable  # Main callback to process user state.

    def __init__(self, *args, callback:Callable, **kwargs):
        self._callback = callback
        super().__init__(*args, **kwargs)

    def do_POST(self) -> None:
        """ Service a POST request. """
        size = int(self.headers["Content-Length"])
        data = self.rfile.read(size)
        self._callback(data, self.finish_POST)

    def finish_POST(self, response:bytes) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)


class _GUIHTTP_VIEW(GUIHTTP):

    @VIEW.VIEWAction.response
    def on_view_finished(self, state:ViewState) -> None:
        """ After any action, update the client with the new state. """
        raise NotImplementedError


class HttpServer(_GUIHTTP_VIEW):
    """ Handles the most fundamental operations of the system, including status and exceptions. """

    _ADDRESS = "localhost", 80

    def GUIHTTPServe(self) -> int:
        """ Add data kwargs to every instantiated handler. """
        handler_cls_with_data = partial(SpectraRequestHandler, directory=self._HTTP_PUBLIC, callback=self.run)
        httpd = HTTPServer(self._ADDRESS, handler_cls_with_data)
        return httpd.serve_forever()

    def run(self, data:bytes, req_call:Callable) -> None:
        """ Process a state obtained from a client query string. Attach the callback so we don't lose it. """
        state = ViewState.decode(data)
        state._req = req_call
        self.VIEWAction(state)

    def on_view_finished(self, state:ViewState) -> None:
        """ Encode any changes and send them back to the client with the callback. """
        state._req(state.encode())
