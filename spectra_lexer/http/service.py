""" Contains classes for handling specific use cases of HTTP.

    Router  - delegates requests to other request handlers based on the headers.
    Filter  - modifies responses generated by a child request handler.
    Service - generates response objects directly as an endpoint of the request handler chain. """

import gzip
from mimetypes import MimeTypes
import os

from .request import HTTPRequest
from .response import HTTPResponse, HTTPResponseHeaders
from .status import HTTPError


class HTTPRequestHandler:
    """ Interface for a processor of HTTP requests. """

    def __call__(self, request:HTTPRequest) -> HTTPResponse:
        """ Return a response object given a request object. Must be completely thread-safe. """
        raise NotImplementedError


class HTTPMethodRouter(HTTPRequestHandler):
    """ Delegates requests to other request handlers based on uppercase HTTP method. """

    def __init__(self) -> None:
        self._handlers = {}  # Table of HTTP request handlers by uppercase HTTP method.

    def add_route(self, method:str, handler:HTTPRequestHandler) -> None:
        self._handlers[method.upper()] = handler

    def __call__(self, request:HTTPRequest) -> HTTPResponse:
        """ Route HTTP requests by method. """
        method = request.method.upper()
        handler = self._handlers.get(method)
        if handler is None:
            raise HTTPError.NOT_IMPLEMENTED(method)
        response = handler(request)
        # Remove any content body if the method is HEAD.
        if method == "HEAD":
            response.content = b''
        return response


class HTTPPathRouter(HTTPRequestHandler):
    """ Delegates requests to other request handlers based on lowercase URI path. """

    def __init__(self, default:HTTPRequestHandler=None) -> None:
        self._handlers = {}              # Table of HTTP request handlers by lowercase URI path.
        self._default_handler = default  # Optional handler to use when no path matches.

    def add_route(self, path:str, handler:HTTPRequestHandler) -> None:
        self._handlers[path.lower()] = handler

    def __call__(self, request:HTTPRequest) -> HTTPResponse:
        """ Route HTTP requests by URI path. """
        path = request.uri.path
        handler = self._handlers.get(path.lower(), self._default_handler)
        if handler is None:
            raise HTTPError.NOT_FOUND(path)
        return handler(request)


class HTTPContentTypeRouter(HTTPRequestHandler):
    """ Delegates requests to other request handlers based on content type. """

    def __init__(self) -> None:
        self._handlers = {}  # Table of HTTP request handlers by content type.

    def add_route(self, mime_type:str, handler:HTTPRequestHandler) -> None:
        self._handlers[mime_type] = handler

    def __call__(self, request:HTTPRequest) -> HTTPResponse:
        """ Route HTTP requests by content type. """
        mime_type = request.headers.content_type()
        if not mime_type:
            raise HTTPError.UNPROCESSABLE_ENTITY("Content-Type is missing.")
        handler = self._handlers.get(mime_type)
        if handler is None:
            raise HTTPError.UNSUPPORTED_MEDIA_TYPE(mime_type)
        return handler(request)


class HTTPGzipFilter(HTTPRequestHandler):

    def __init__(self, handler:HTTPRequestHandler, *, compresslevel=9, size_threshold=0) -> None:
        self._handler = handler                # Child request handler.
        self._compresslevel = compresslevel    # Compression level from 1 (fastest) to 9 (slowest).
        self._size_threshold = size_threshold  # Only compress content at least this size in bytes.

    def __call__(self, request:HTTPRequest) -> HTTPResponse:
        """ Compress the content of the response if it meets our conditions. """
        response = self._handler(request)
        data = response.content
        if data is not None and request.headers.accept_gzip() and len(data) >= self._size_threshold:
            gzip_data = gzip.compress(data, self._compresslevel)
            # Don't use the compressed data unless it is actually smaller.
            if len(gzip_data) < len(data):
                response.content = gzip_data
                response.headers.set_content_length(len(gzip_data))
                response.headers.set_content_encoding('gzip')
        return response


class HTTPFileService(HTTPRequestHandler):
    """ Handles requests specific to file retrieval (generally using GET and HEAD methods). """

    def __init__(self, directory:str, index_filename="index.html") -> None:
        self._directory = directory   # Root directory for public HTTP file requests.
        self._index = index_filename  # When a directory path is accessed, redirect to this landing page inside it.
        self._types = MimeTypes()     # Called to find MIME types for files based on their paths.

    def __call__(self, request:HTTPRequest) -> HTTPResponse:
        """ Common file-serving code for GET and HEAD commands. """
        uri_path = request.uri.path
        file_path = self._translate_path(uri_path)
        try:
            return self._file_response(file_path, request)
        except OSError:
            raise HTTPError.NOT_FOUND(uri_path)

    def _file_response(self, file_path:str, request:HTTPRequest) -> HTTPResponse:
        """ Open a file and send it in the response if it exists and was not cached recently. """
        with open(file_path, 'rb') as fp:
            fs = os.fstat(fp.fileno())
            mtime = fs.st_mtime
            headers = HTTPResponseHeaders()
            if not request.headers.modified_since(mtime):
                response = HTTPResponse.NOT_MODIFIED(headers)
            else:
                headers.set_last_modified(mtime)
                mime_type = self._types.guess_type(file_path)[0]
                content = fp.read()
                headers.set_content_type(mime_type)
                headers.set_content_length(len(content))
                response = HTTPResponse.OK(headers, content)
            return response

    def _translate_path(self, uri_path:str) -> str:
        """ Translate <uri_path> to the local filename syntax.
            Ignore path components that are not files/directory names, or which point above the root folder. """
        new_comps = []
        for comp in uri_path.strip().split('/'):
            if comp and comp != '.' and not os.path.dirname(comp):
                if comp == '..':
                    if new_comps:
                        new_comps.pop()
                else:
                    new_comps.append(comp)
        file_path = os.path.join(self._directory, *new_comps)
        # Route bare directory paths to the index (whether or not it exists).
        if os.path.isdir(file_path):
            file_path = os.path.join(file_path, self._index)
        return file_path


class HTTPDataService(HTTPRequestHandler):
    """ Abstract class; decodes binary data from HTTP content, processes it, and returns an encoded result. """

    output_type: str  # Required - MIME type of output data.

    def __call__(self, request:HTTPRequest) -> HTTPResponse:
        """ Process content obtained from a client. If successful, send the returned data back to the client. """
        data_in = request.content
        data_out = self.process(data_in)
        headers = HTTPResponseHeaders()
        headers.set_content_type(self.output_type)
        headers.set_content_length(len(data_out))
        return HTTPResponse.OK(headers, data_out)

    def process(self, data:bytes) -> bytes:
        """ Subclass method to process binary data. """
        raise NotImplementedError
