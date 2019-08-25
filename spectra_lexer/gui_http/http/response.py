import email.utils
from functools import partial
from http import HTTPStatus
from io import RawIOBase


class HTTPStructMeta(type):
    """ Convenience metaclass for structures that use an HTTP status code as their first argument. """

    def __getattr__(cls, name:str) -> partial:
        """ Create an instance corresponding directly to a member of HTTPStatus. """
        code = getattr(HTTPStatus, name)
        return partial(cls, code)


class HTTPResponse(metaclass=HTTPStructMeta):
    """ Describes the outcome of an HTTP request with a status line and a series of headers and/or content. """

    # Ordered table of HTTP header formatting functions. General headers are first, entity headers are last.
    HEADER_TYPES = [('date',     lambda _: f'Date: {email.utils.formatdate(usegmt=True)}'),
                    ('server',   lambda s: f'Server: {s}'),
                    ('close',    lambda _: f'Connection: close'),
                    ('modified', lambda f: f'Last-Modified: {email.utils.formatdate(f, usegmt=True)}'),
                    ('ctype',    lambda s: f'Content-Type: {s}'),
                    ('content',  lambda b: f'Content-Length: {len(b)}')]

    _status: str   # HTTP status line.
    _params: dict  # Initial parameters from which to build headers.

    def __init__(self, code:HTTPStatus, **params) -> None:
        self._status = f'HTTP/1.1 {code} {code.phrase}'
        self._params = params

    def send(self, stream:RawIOBase, **params) -> str:
        """ Add additional header parameters, then parse each one into a header line. """
        d = {**self._params, **params}
        headers = [fn(d[k]) for k, fn in self.HEADER_TYPES if k in d]
        # Add the status line header and the blank line endings, then write everything.
        full_header = "\r\n".join([self._status, *headers, "", ""])
        stream.write(full_header.encode('latin-1', 'strict'))
        # If there was a content section, write it unless the request method was HEAD.
        if 'content' in d and not d.get('head'):
            stream.write(d["content"])
        # Return the status line as the string value of the response.
        return self._status


class HTTPError(Exception, metaclass=HTTPStructMeta):

    # The message body is omitted for 1xx, 204 (No Content), 205 (Reset Content), 304 (Not Modified).
    NO_BODY_CODES = {*range(100, 200), HTTPStatus.NO_CONTENT, HTTPStatus.RESET_CONTENT, HTTPStatus.NOT_MODIFIED}
    HTML_SUB = str.maketrans({"&": "&amp;", "<": "&lt;", ">": "&gt;"})

    response: HTTPResponse  # HTTP response with possible encoded HTML document to send to the user.

    def __init__(self, code:HTTPStatus=HTTPStatus.INTERNAL_SERVER_ERROR, *messages:str) -> None:
        """ The first arg must be the HTTP code (default 500). Other args are added as custom messages. """
        head_line = f'HTTP Error {code} - {code.phrase}'
        super().__init__(head_line)
        # Add a header to signal connection close after sending.
        headers = {'close': True}
        if code not in self.NO_BODY_CODES:
            # Add an HTML document explaining the error to the user.
            message_line = ": ".join([code.description, *messages]).translate(self.HTML_SUB)
            body = ('<!DOCTYPE html><html>'
                    '<head><meta http-equiv="Content-Type" content="text/html"></head>'
                    f'<body><h1>{head_line}</h1><h3>{message_line}</h3></body>'
                    '</html>').encode('utf-8', 'replace')
            headers.update(ctype='text/html', content=body)
        self.response = HTTPResponse(code, **headers)
