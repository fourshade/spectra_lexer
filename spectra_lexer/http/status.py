from functools import partial
from http import HTTPStatus


class HTTPResponseStatus:
    """ HTTP status code wrapper for responses. """

    # The content body is omitted for 1xx, 204 (No Content), 205 (Reset Content), 304 (Not Modified).
    _NO_BODY_CODES = {*range(100, 200), HTTPStatus.NO_CONTENT, HTTPStatus.RESET_CONTENT, HTTPStatus.NOT_MODIFIED}
    _HTML_SUB = str.maketrans({"&": "&amp;", "<": "&lt;", ">": "&gt;"})

    def __init__(self, code:HTTPStatus) -> None:
        self._code = code

    def has_body(self) -> bool:
        """ Return True if the response should have a content body. """
        return self._code not in self._NO_BODY_CODES

    def __str__(self) -> str:
        """ Return a short summary of the status for a log. """
        return f'{self._code} {self._code.phrase}'

    def header(self, version="1.1") -> str:
        """ Return a formatted HTTP status line header. """
        return f'HTTP/{version} {self._code} {self._code.phrase}'

    def error_html(self, *args) -> str:
        """ Return an HTML document explaining the error code to the user. """
        message = self._code.description
        if args:
            message += ": " + ", ".join(map(str, args))
        return ('<!DOCTYPE html><html><head>'
                '  <meta http-equiv="Content-Type" content="text/html">'
                '</head><body>'
                f'  <h1>HTTP Error {self._code} - {self._code.phrase}</h1>'
                f'  <h3>{message.translate(self._HTML_SUB)}</h3>'
                '</body></html>')


class HTTPStatusMeta(type):
    """ Convenience metaclass for structures that use an HTTP response status as their first constructor argument. """

    def __getattr__(cls, name:str) -> partial:
        """ Return a factory for instances corresponding directly to a member of HTTPStatus. """
        code = getattr(HTTPStatus, name)
        status = HTTPResponseStatus(code)
        return partial(cls, status)


class HTTPError(Exception, metaclass=HTTPStatusMeta):
    """ Exception corresponding directly to a standard HTTP error. """

    _DEFAULT_STATUS = HTTPResponseStatus(HTTPStatus.INTERNAL_SERVER_ERROR)

    def __init__(self, status:HTTPResponseStatus=_DEFAULT_STATUS, *args) -> None:
        """ The first arg must be the HTTP status (default 500). Other args are shown in error messages. """
        super().__init__(*args)
        self.status = status
