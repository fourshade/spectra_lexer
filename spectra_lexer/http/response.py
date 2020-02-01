import email.utils
from typing import BinaryIO, Iterator

from .status import HTTPError, HTTPResponseStatus, HTTPStatusMeta


class HTTPResponseHeaders:
    """ Structure for HTTP response headers (other than the status line). """

    # Ordered list of response headers. General headers are first, entity headers are last.
    HEADER_TYPES = ['Date', 'Server', 'Connection', 'Last-Modified',
                    'Content-Type', 'Content-Encoding', 'Content-Length']

    def __init__(self) -> None:
        self._d = {}  # String dict with each header.

    @staticmethod
    def _format_date(timeval:float=None) -> str:
        return email.utils.formatdate(timeval, usegmt=True)

    def set_date(self) -> None:
        self._d["Date"] = self._format_date()

    def set_server(self, server:str) -> None:
        self._d["Server"] = server

    def set_connection_close(self) -> None:
        self._d["Connection"] = "close"

    def set_last_modified(self, mtime:float) -> None:
        self._d["Last-Modified"] = self._format_date(mtime)

    def set_content_type(self, mime_type:str) -> None:
        self._d["Content-Type"] = mime_type

    def set_content_encoding(self, encoding:str) -> None:
        self._d["Content-Encoding"] = encoding

    def set_content_length(self, length:int) -> None:
        self._d["Content-Length"] = str(length)

    def iter_lines(self) -> Iterator[str]:
        """ Yield each header line in order. """
        d = self._d
        for k in self.HEADER_TYPES:
            if k in d:
                yield f'{k}: {d[k]}'


class HTTPResponse(metaclass=HTTPStatusMeta):
    """ Class representing the outcome of an HTTP/1.1 request with a status line, headers, and/or content. """

    def __init__(self, status:HTTPResponseStatus, headers:HTTPResponseHeaders, content=b'') -> None:
        self.status = status
        self.headers = headers
        self.content = content

    def __str__(self) -> str:
        """ Return a summary of the response for a log. """
        return str(self.status)


class HTTPResponseWriter:
    """ Writes HTTP response headers and content to a binary stream. """

    def __init__(self, stream:BinaryIO, server_version:str=None) -> None:
        self._stream = stream                  # Writable ISO-8859-1 binary stream.
        self._server_version = server_version  # Server version string sent with each response.

    def write(self, response:HTTPResponse) -> str:
        """ Add standard headers, the status line, and blank line endings.
            Write everything to the ISO-8859-1 binary stream and return the status log string. """
        status = response.status
        headers = response.headers
        headers.set_date()
        if self._server_version is not None:
            headers.set_server(self._server_version)
        header_lines = [status.header(), *headers.iter_lines(), "", ""]
        header_data = "\r\n".join(header_lines).encode('iso-8859-1', 'strict')
        self._stream.write(header_data)
        self._stream.write(response.content)
        return str(status)

    def write_continue(self) -> str:
        """ Write a continue response and return the status. This cannot have a message body. """
        headers = HTTPResponseHeaders()
        response = HTTPResponse.CONTINUE(headers)
        return self.write(response)

    def write_error(self, e:HTTPError) -> str:
        """ Write an error response and return the status. This closes the connection. """
        status = e.status
        headers = HTTPResponseHeaders()
        headers.set_connection_close()
        content = None
        if status.has_body():
            html_text = status.error_html(*e.args)
            content = html_text.encode('utf-8', 'replace')
            headers.set_content_type('text/html')
            headers.set_content_length(len(content))
        response = HTTPResponse(status, headers, content)
        return self.write(response)
