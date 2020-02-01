import datetime
import email.utils
from typing import BinaryIO, Dict, Iterable, Iterator, Mapping, Optional

from .status import HTTPError


class HTTPRequestHeaders:
    """ Structure for HTTP headers (other than the request line). """

    def __init__(self, header_map:Mapping[str, str]) -> None:
        self._d = header_map  # String mapping with the last header under each unique lowercased name.

    def _get_lower(self, name:str) -> str:
        return self._d.get(name.lower(), "")

    def content_type(self) -> str:
        """ Return the media type/subtype in lowercase, discarding any comments. """
        ctype = self._get_lower("Content-Type")
        if ";" in ctype:
            ctype = ctype.split(";", 1)[0].strip()
        return ctype.lower()

    def content_length(self) -> int:
        """ Return the content length in bytes if the header is present; 0 otherwise. """
        return int(self._get_lower("Content-Length") or 0)

    def accept_gzip(self) -> bool:
        """ Return True if the client accepts the gzip encoding method. """
        return 'gzip' in self._get_lower("Accept-Encoding").lower()

    def expect_continue(self) -> bool:
        """ Return True if the client is expecting a 100 Continue before it sends any more data. """
        return self._get_lower('Expect').lower() == "100-continue"

    def keep_alive(self) -> bool:
        """ Return True if the connection should be kept alive after this request. """
        return self._get_lower('Connection').lower() != 'close'

    def modified_since(self, mtime:float) -> bool:
        """ Return True if one of the following applies (meaning content must be sent/resent):
            - the file modification timestamp <mtime> is later than the If-Modified-Since header.
            - there is no If-Modified-Since header.
            - there is an If-None-Match header, which overrides If-Modified-Since. """
        if self._get_lower("If-None-Match"):
            return True
        header_mtime = self._get_lower("If-Modified-Since")
        if not header_mtime:
            return True
        try:
            ims = email.utils.parsedate_to_datetime(header_mtime)
            last_modif = datetime.datetime.fromtimestamp(mtime, datetime.timezone.utc)
            last_modif = last_modif.replace(microsecond=0)
            return last_modif > ims
        except (TypeError, IndexError, OverflowError, ValueError):
            return True

    @classmethod
    def from_lines(cls, lines:Iterable[str]) -> "HTTPRequestHeaders":
        """ Parse headers from raw string form, even those with duplicate names. """
        raw = []
        for line in lines:
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
        return cls(d)


class HTTPRequestURI:
    """ Structure representing the parts of an HTTP request URI. """

    # Maps two-digit hex strings to corresponding characters in the ASCII range.
    _HEX_SUB = {bytes([b]).hex(): chr(b) for b in range(128)}

    def __init__(self, path:str, query:Dict[str, str], fragment:str) -> None:
        self.path = path          # URI path (everything from the root / to the query ?).
        self.query = query        # URI query (everything from the ? to the #), parsed into a string dict.
        self.fragment = fragment  # URI fragment (everything after the #).

    @classmethod
    def from_string(cls, s:str) -> "HTTPRequestURI":
        """ Parse a URI from string form, unquoting special characters. """
        unquote = cls._unquote_plus
        fragment = ''
        if '#' in s:
            s, raw_fragment = s.split('#', 1)
            fragment = unquote(raw_fragment)
        query_dict = {}
        if '?' in s:
            s, query = s.split('?', 1)
            pairs = [s2.split('=', 1) for s1 in query.split('&') for s2 in s1.split(';') if '=' in s2]
            query_dict = {unquote(k): unquote(v) for k, v in pairs}
        path = unquote(s)
        return cls(path, query_dict, fragment)

    @classmethod
    def _unquote_plus(cls, string:str) -> str:
        """ Replace + and %xx escapes by their single-character equivalent. """
        if '+' in string:
            string = string.replace('+', ' ')
        if '%' not in string:
            return string
        first, *bits = string.split('%')
        res = [first]
        for item in bits:
            try:
                res += cls._HEX_SUB[item[:2].lower()], item[2:]
            except KeyError:
                res += '%', item
        return ''.join(res)


class HTTPRequest:
    """ Structure representing an HTTP/1.1 request.
        Other versions should work, though headers may not be recognized. """

    def __init__(self, method:str, uri:HTTPRequestURI, headers:HTTPRequestHeaders, content:bytes) -> None:
        self.method = method    # HTTP method string (GET, POST, etc.)
        self.uri = uri          # HTTP URI starting from the server root.
        self.headers = headers  # HTTP request headers, unordered, with lowercase keys.
        self.content = content  # The rest of the data read from the HTTP stream, as a byte string.


class HTTPRequestReader:
    """ Reads HTTP request headers and content from a binary stream. """

    def __init__(self, stream:BinaryIO, max_header_size=65536) -> None:
        self._stream = stream                    # Readable ISO-8859-1 binary stream.
        self._max_header_size = max_header_size  # Maximum combined size of headers in bytes.

    def read(self) -> Optional[HTTPRequest]:
        """ Parse HTTP request data from the current stream into a request object.
            If there was no data at all, return None. """
        header_lines = list(self._readline_headers())
        if header_lines:
            return self._parse(*header_lines)

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

    def _parse(self, request_line:str, *other_lines:str) -> HTTPRequest:
        """ Parse the request line into a method, URI components, and HTTP request version. """
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
        uri_obj = HTTPRequestURI.from_string(uri)
        headers = HTTPRequestHeaders.from_lines(other_lines)
        content = self._stream.read(headers.content_length())
        return HTTPRequest(method, uri_obj, headers, content)
