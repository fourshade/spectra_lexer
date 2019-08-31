import datetime
import email.utils
from io import RawIOBase
from typing import Dict, Iterable, Iterator, Optional, Tuple

from .response import HTTPError


class HTTPRequestHeaders:
    """ Mapping structure for HTTP headers. """

    def __init__(self, h_dict:Dict[str, str]) -> None:
        self._d = h_dict  # String dict with the last header under each unique lowercased name.

    def _get_lower(self, name:str) -> str:
        return self._d.get(name.lower(), "")

    def content_length(self) -> int:
        return int(self._get_lower("Content-Length") or 0)

    def expect_continue(self) -> bool:
        """ Return True if the client is expecting a 100 Continue before it sends any more data. """
        return self._get_lower('Expect').lower() == "100-continue"

    def keep_alive(self) -> bool:
        """ Return True if the connection should be kept alive after this request. """
        return self._get_lower('Connection').lower() != 'close'

    def modified_time(self) -> Optional[str]:
        """ Return the file modification timestamp, or None if it will be overridden by If-None-Match. """
        if not self._get_lower("If-None-Match"):
            return self._get_lower("If-Modified-Since")


class HTTPRequest:
    """ Class representing an HTTP/1.1 request. Other versions should work, though headers may not be recognized. """

    def __init__(self, method:str, path:str, query:Dict[str, str], headers:HTTPRequestHeaders, content:bytes) -> None:
        self.method = method     # HTTP method string (GET, POST, etc.)
        self.path = path         # URI path (everything from the root / to the query ?)
        self.query = query       # URI query (everything from the ? to the #), parsed into a string dict.
        self.headers = headers   # HTTP request headers, unordered, with lowercase keys.
        self.content = content   # The rest of the data read from the HTTP stream, as a byte string.

    def modified_since(self, mtime:float) -> bool:
        """ Return True if the given file modification timestamp is later than If-Modified-Since in the header.
            If there is no modification header, we must always resend the content, so return True there as well. """
        header_mtime = self.headers.modified_time()
        if not header_mtime:
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


class HTTPRequestParser:
    """ Parses HTTP request headers and content from a text stream. """

    # Maps two-digit hex strings to corresponding characters in the ASCII range.
    _HEX_SUB = {bytes([b]).hex(): chr(b) for b in range(128)}

    def __init__(self, stream:RawIOBase, max_header_size:int=65536) -> None:
        self._stream = stream                    # Readable TCP stream.
        self._max_header_size = max_header_size  # Maximum combined size of headers in bytes.

    def read(self) -> Optional[HTTPRequest]:
        """ Parse HTTP request data from the current stream into a request object. """
        return self._parse(*self._readline_headers())

    def _readline_headers(self) -> Iterator[str]:
        """ Read and decode each header line as a string, up to the total maximum size. """
        size_left = self._max_header_size
        for line in self._stream:
            size_left -= len(line)
            if size_left < 0:
                raise HTTPError.REQUEST_HEADER_FIELDS_TOO_LARGE()
            line = line.decode('iso-8859-1').strip()
            if not line:
                break
            yield line

    def _parse(self, request_line:str="", *header_lines:str) -> Optional[HTTPRequest]:
        """ Parse the request line into a method, URI components, and HTTP request version.
            If the request was badly formed, raise an error; if there was no data at all, return None. """
        if not request_line:
            return None
        try:
            method, uri, version = request_line.split()
            if not version.startswith('HTTP/'):
                raise ValueError
            major, minor = version[5:].split(".")
            # Only HTTP/1.x is supported.
            if int(major) != 1:
                raise HTTPError.HTTP_VERSION_NOT_SUPPORTED(version)
        except ValueError:
            raise HTTPError.BAD_REQUEST(request_line)
        path, query, fragment = self._parse_uri(uri)
        # Parse the headers, get any content, and put the request structure together.
        h_dict = self._parse_headers(header_lines)
        headers = HTTPRequestHeaders(h_dict)
        content = self._stream.read(headers.content_length())
        return HTTPRequest(method, path, query, headers, content)

    def _parse_uri(self, uri:str) -> Tuple[str, dict, str]:
        """ Parse the URI into components. """
        sfragment = ''
        if '#' in uri:
            uri, fragment = uri.split('#', 1)
            sfragment = self._unquote_plus(fragment)
        squery = {}
        if '?' in uri:
            unquote = self._unquote_plus
            uri, query = uri.split('?', 1)
            pairs = [s2.split('=', 1) for s1 in query.split('&') for s2 in s1.split(';') if '=' in s2]
            squery = {unquote(k): unquote(v) for k, v in pairs}
        path = self._unquote_plus(uri)
        return path, squery, sfragment

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

    def _parse_headers(self, header_lines:Iterable[str]) -> Dict[str, str]:
        """ Parse the raw string form of every header, even those with duplicate names, into a dict and return it. """
        raw = []
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
        d = {}
        for source in raw:
            # The name is parsed as everything up to the ':' and returned unmodified.
            # The value is determined by stripping leading whitespace and trailing newline characters.
            name, *values = source
            value = ''.join(values).lstrip().rstrip('\r\n')
            d[name.lower()] = value
        return d
