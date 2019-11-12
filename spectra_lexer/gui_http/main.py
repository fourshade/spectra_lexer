import os
import sys
from threading import Lock

from .http import HTTPFileGetter, HTTPJSONProcessor, HTTPMethodTable, HTTPServer
from spectra_lexer.app import StenoApplication
from spectra_lexer.base import StenoAppFactory, StenoAppOptions
from spectra_lexer.cmdline import CmdlineOption
from spectra_lexer.steno import StenoAnalysis, StenoAnalysisPage, SearchResults


class StenoAppProcessor(HTTPJSONProcessor):
    """ The main app code may not be thread-safe. This wrapper will process only one response at a time. """

    def __init__(self, app:StenoApplication, **kwargs) -> None:
        super().__init__(**kwargs)
        self._process = app.process_action
        self._lock = Lock()

    def process(self, state:dict, path:str, *args) -> dict:
        """ The decoded object is the state dict, and the relative path includes the action. """
        action = path.split('/')[-1]
        with self._lock:
            return self._process(state, action)

    def convert_bytes(self, obj:bytes) -> str:
        """ Encode XML steno board bytes data as a string with the current encoding. """
        return obj.decode(self.encoding)

    def add_data_class(self, data_cls:type) -> None:
        """ Add a conversion method for a data class, whose instance attributes may be encoded
            directly into a JSON object. This uses vars(), so classes that use __slots__ are not allowed.
            For this to work, each attribute must contain either a JSON-compatible type or another data class.
            Since type information is not encoded, this conversion is strictly one-way. """
        setattr(self, f"convert_{data_cls.__name__}", vars)


class HttpAppOptions(StenoAppOptions):

    HTTP_PUBLIC_DEFAULT = os.path.join(os.path.split(__file__)[0], "public")

    address: str = CmdlineOption("--http-addr", "", "IP address or hostname for server.")
    port: int = CmdlineOption("--http-port", 80, "TCP port to listen for connections.")
    directory: str = CmdlineOption("--http-dir", HTTP_PUBLIC_DEFAULT, "Root directory for public HTTP file service.")


def http() -> int:
    """ Run the Spectra HTTP web application. """
    options = HttpAppOptions(__doc__)
    options.parse()
    factory = StenoAppFactory(options)
    log = factory.build_logger().log
    log("Loading...")
    app = factory.build_app()
    processor = StenoAppProcessor(app)
    for cls in [SearchResults, StenoAnalysis, StenoAnalysisPage]:
        processor.add_data_class(cls)
    fgetter = HTTPFileGetter(options.directory)
    method_handler = HTTPMethodTable(GET=fgetter, HEAD=fgetter, POST=processor)
    server = HTTPServer(method_handler, log, threaded=True)
    # Start the server and poll for connections indefinitely.
    log("Server started.")
    try:
        server.start(options.address, options.port)
    finally:
        server.shutdown()
    log("Server stopped.")
    return 0


if __name__ == '__main__':
    sys.exit(http())
