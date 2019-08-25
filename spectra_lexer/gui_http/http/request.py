import datetime
import email.utils
from io import RawIOBase
from typing import Iterator

from .response import HTTPError


class HTTPRequestURI:

    _HEX_SUB = {bytes([b]).hex(): chr(b) for b in range(128)}

    path: str
    query: dict
    fragment: str = ''

    def __init__(self, uri:str):
        """ Parse the URI into components. """
        unquote = self._unquote_plus
        if '#' in uri:
            uri, fragment = uri.split('#', 1)
            self.fragment = unquote(fragment)
        self.query = {}
        if '?' in uri:
            uri, query = uri.split('?', 1)
            pairs = [s2.split('=', 1) for s1 in query.split('&') for s2 in s1.split(';') if '=' in s2]
            self.query = {unquote(k): unquote(v) for k, v in pairs}
        self.path = unquote(uri)

    def _unquote_plus(self, string:str) -> str:
        """ Replace + and %xx escapes by their single-character equivalent. """
        if '+' in string:
            string = string.replace('+', ' ')
        if '%' not in string:
            return string
        first, *bits = string.split('%')
        res = [first]
        for item in bits:
            try:
                res += self._HEX_SUB[item[:2].lower()], item[2:]
            except KeyError:
                res += '%', item
        return ''.join(res)


class HTTPRequestHeaders:
    """ Mapping structure for HTTP headers. """

    raw: list  # Contains the raw string form of every header, even those with duplicate names.
    _d: dict   # Contains the last header with each unique lowercased name.

    def __init__(self, header_lines:list):
        # Create a new message and start by parsing headers.
        self.raw = raw = []
        self._d = d = {}
        for line in header_lines:
            # Search for a line with no colon (including an empty line).
            if ':' not in line:
                # Check for continuation, otherwise quit. A first line continuation is illegal.
                if line and line[0] in ' \t' and raw:
                    raw[-1].append(line)
                    continue
                break
            # Split the line on the colon separating field name from value. There will always be a colon at this point.
            raw.append(line.split(':', 1))
        for source in raw:
            # The name is parsed as everything up to the ':' and returned unmodified.
            # The value is determined by stripping leading whitespace and trailing newline characters.
            name, *values = source
            value = ''.join(values).lstrip().rstrip('\r\n')
            source[:] = name, value
            d[name.lower()] = value

    def get(self, name:str, *args) -> str:
        return self._d.get(name.lower(), *args)


class HTTPRequest:
    """ Class representing an HTTP/1.1 request. Other versions should work, though headers may not be recognized. """

    MAX_HEADER_SIZE = 65536   # Maximum combined size of headers in bytes.

    method: str = ''
    path: str = ''
    query: dict = {}
    content: bytes = b""

    _headers = {}

    def __init__(self, stream:RawIOBase):
        """ Parse HTTP request data from a stream object. """
        request_line, *header_lines = [*self._readline_headers(stream), ""]
        if not request_line:
            return
        self._parse_requestline(request_line)
        self._headers = HTTPRequestHeaders(header_lines)
        len_str = self._headers.get("Content-Length")
        if len_str is not None:
            self.content = stream.read(int(len_str))

    def _readline_headers(self, stream:RawIOBase) -> Iterator[str]:
        """ Read and decode each header line as a string. """
        size_left = self.MAX_HEADER_SIZE
        for line in stream:
            size_left -= len(line)
            if size_left < 0:
                raise HTTPError.REQUEST_HEADER_FIELDS_TOO_LARGE()
            line = line.decode('iso-8859-1').strip()
            if not line:
                break
            yield line

    def _parse_requestline(self, request_line:str) -> None:
        """ Parse the request line into a method, URI components, and HTTP request version.  """
        try:
            self.method, uri, version = request_line.split()
            if not version.startswith('HTTP/'):
                raise ValueError
            major, minor = version[5:].split(".")
            # Only HTTP/1.x is supported.
            if int(major) != 1:
                raise HTTPError.HTTP_VERSION_NOT_SUPPORTED(version)
        except ValueError:
            raise HTTPError.BAD_REQUEST(request_line)
        uri = HTTPRequestURI(uri)
        self.path = uri.path
        self.query = uri.query

    def expect_continue(self) -> bool:
        """ Return True if the client is expecting a 100 Continue before it sends any more data. """
        return self._headers.get('Expect', "").lower() == "100-continue"

    def keep_alive(self) -> bool:
        """ Return True if the connection should be kept alive after this request. """
        return self._headers.get('Connection', "").lower() != 'close'

    def modified_since(self, mtime:float) -> bool:
        """ Return True if the given file modification timestamp is later than If-Modified-Since in the header. """
        header_mtime = self._headers.get("If-Modified-Since")
        none_match = self._headers.get("If-None-Match")
        if header_mtime is None or none_match is not None:
            return True
        try:
            ims = email.utils.parsedate_to_datetime(header_mtime)
            last_modif = datetime.datetime.fromtimestamp(mtime, datetime.timezone.utc)
            last_modif = last_modif.replace(microsecond=0)
            return last_modif > ims
        except (TypeError, IndexError, OverflowError, ValueError):
            return True

    def __str__(self) -> str:
        """ Return a summary of the request for a log. """
        return f'{self.method} {self.path}'
