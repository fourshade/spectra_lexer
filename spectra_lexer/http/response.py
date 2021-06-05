import email.utils
from typing import BinaryIO, Iterator

from .status import HTTPResponseStatus, HTTPStatusMeta


def _format_date(timeval:float=None) -> str:
    return email.utils.formatdate(timeval, usegmt=True)


class HTTPResponseHeaders:
    """ Structure for HTTP response headers (other than the status line). """

    # Ordered list of response headers. General headers are first, entity headers are last.
    HEADER_TYPES = ['Date', 'Server', 'Connection', 'Last-Modified',
                    'Content-Type', 'Content-Encoding', 'Content-Length']

    def __init__(self) -> None:
        self._d = {}  # String dict with each header.

    def set_date(self) -> None:
        self._d['Date'] = _format_date()

    def set_server(self, server:str) -> None:
        self._d['Server'] = server

    def set_connection_close(self) -> None:
        self._d['Connection'] = 'close'

    def set_last_modified(self, mtime:float) -> None:
        self._d['Last-Modified'] = _format_date(mtime)

    def set_content_type(self, mime_type:str) -> None:
        self._d['Content-Type'] = mime_type

    def set_content_encoding(self, encoding:str) -> None:
        self._d['Content-Encoding'] = encoding

    def set_content_length(self, length:int) -> None:
        self._d['Content-Length'] = str(length)

    def iter_lines(self) -> Iterator[str]:
        """ Yield each header line in order (without newlines). """
        d = self._d
        for k in self.HEADER_TYPES:
            if k in d:
                yield f'{k}: {d[k]}'


class HTTPResponse(metaclass=HTTPStatusMeta):
    """ Structure representing the outcome of an HTTP/1.1 request with a status line, headers, and/or content. """

    def __init__(self, status:HTTPResponseStatus, headers:HTTPResponseHeaders, content=b'') -> None:
        self.status = status    # Status code.
        self.headers = headers  # Response headers.
        self.content = content  # Binary content data.


class HTTPResponseWriter:
    """ Writes HTTP response headers and content to a binary stream. """

    def __init__(self, stream:BinaryIO) -> None:
        self._stream = stream  # Writable ISO-8859-1 binary stream.

    def write(self, response:HTTPResponse) -> None:
        """ Write a full HTTP response to the stream. """
        header_lines = [response.status.header(), *response.headers.iter_lines(), '', '']
        header_data = '\r\n'.join(header_lines).encode('iso-8859-1', 'strict')
        self._stream.write(header_data)
        self._stream.write(response.content)
