""" Contains classes specifically for handling certain use cases of HTTP methods. """

import json
from mimetypes import MimeTypes
import os
from typing import Any, Union

from .request import HTTPRequest
from .response import HTTPResponse, HTTPError


class HTTPRequestHandler:
    """ Interface for an HTTP data processor that creates a response object from a request object. """

    def __call__(self, request:HTTPRequest) -> HTTPResponse:
        raise NotImplementedError


class HTTPMethodRouter(HTTPRequestHandler):
    """ Delegates requests to other request handlers based on HTTP method. """

    def __init__(self) -> None:
        self._handlers = {}  # Table of HTTP request handlers by uppercase HTTP method.

    def add_route(self, method:str, handler:HTTPRequestHandler) -> None:
        self._handlers[method.upper()] = handler

    def __call__(self, request:HTTPRequest) -> HTTPResponse:
        """ Route HTTP requests by method. Handlers must be completely thread safe. """
        method = request.method.upper()
        handler = self._handlers.get(method)
        if handler is None:
            raise HTTPError.NOT_IMPLEMENTED(method)
        return handler(request)


class HTTPPathRouter(HTTPRequestHandler):
    """ Delegates requests to other request handlers based on URI path. """

    def __init__(self, default:HTTPRequestHandler=None) -> None:
        self._handlers = {}              # Table of HTTP request handlers by lowercase URI path.
        self._default_handler = default  # Optional handler to use when no path matches.

    def add_route(self, path:str, handler:HTTPRequestHandler) -> None:
        self._handlers[path.lower()] = handler

    def __call__(self, request:HTTPRequest) -> HTTPResponse:
        """ Route HTTP requests by path. Handlers must be completely thread safe. """
        uri_path = request.path.lower()
        handler = self._handlers.get(uri_path, self._default_handler)
        if handler is None:
            raise HTTPError.NOT_FOUND(uri_path)
        return handler(request)


class HTTPFileService(HTTPRequestHandler):
    """ Handles requests specific to file retrieval (generally using GET and HEAD methods). """

    def __init__(self, directory:str, index_filename="index.html") -> None:
        self._directory = directory   # Root directory for public HTTP file requests.
        self._index = index_filename  # When a directory path is accessed, redirect to this landing page inside it.
        self._types = MimeTypes()     # Called to find MIME types for files based on their paths.

    def __call__(self, request:HTTPRequest) -> HTTPResponse:
        """ Common file-serving code for GET and HEAD commands. """
        uri_path = request.path
        file_path = self._translate_path(uri_path)
        try:
            return self.file_response(file_path, request)
        except OSError:
            raise HTTPError.NOT_FOUND(uri_path)

    def file_response(self, file_path:str, request:HTTPRequest) -> HTTPResponse:
        """ Open a file and send it in the response if it exists and was not cached recently. """
        with open(file_path, 'rb') as f:
            fs = os.fstat(f.fileno())
            mtime = fs.st_mtime
            if not request.modified_since(mtime):
                return HTTPResponse.NOT_MODIFIED()
            ctype = self._types.guess_type(file_path)[0]
            # We must skip the content body if the command is HEAD.
            head = (request.method == "HEAD")
            return HTTPResponse.OK(modified=mtime, ctype=ctype, content=f.read(), head=head)

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
    """ Abstract class; handles requests specific to data processing (generally using the POST method). """

    ctype = "text/html"  # MIME content type for outgoing data.

    def __call__(self, request:HTTPRequest) -> HTTPResponse:
        """ Process content, path, and query data obtained from a client.
            If successful, encode the returned object and send it back to the client. """
        try:
            data_in = request.content
            obj_in = self.decode(data_in)
            obj_out = self.process(obj_in, request.path, request.query)
            data_out = self.encode(obj_out)
            return HTTPResponse.OK(ctype=self.ctype, content=data_out)
        except Exception as e:
            raise HTTPError.INTERNAL_SERVER_ERROR() from e

    def decode(self, data:bytes) -> object:
        """ Validate and decode incoming data from a client. This data could contain ANYTHING...beware! """
        raise NotImplementedError

    def process(self, obj_in:object, path:str, query:dict) -> object:
        """ Process the input object into an output object given a URI path and query param dict. """
        raise NotImplementedError

    def encode(self, obj:object) -> bytes:
        """ Encode the outgoing object (usually to UTF-8 for text data). """
        raise NotImplementedError


class HTTPJSONService(HTTPDataService):
    """ Abstract class; decodes a JSON object from HTTP content, processes it, and returns a JSON-encoded result. """

    JSONType = Union[None, bool, int, float, str, tuple, list, dict]  # Python types supported by json module.

    ctype = "application/json"
    encoding = "utf-8"

    def __init__(self, *, size_limit=100000, char_limits=((b"{", 20), (b"[", 20))) -> None:
        self._size_limit = size_limit    # Limit on total size of JSON data in bytes.
        self._char_limits = char_limits  # Limits on special JSON characters.

    def decode(self, data:bytes) -> JSONType:
        """ Validate and decode incoming JSON data from a client. """
        if len(data) > self._size_limit:
            raise ValueError("JSON rejected - data payload too large.")
        # The JSON parser is fast, but dumb. It does naive recursion on containers.
        # The stack can be overwhelmed by a long sequence of '{' and/or '[' characters. Do not let this happen.
        for c, limit in self._char_limits:
            if data.count(c) > limit:
                raise ValueError("JSON rejected - too many containers.")
        return json.loads(data)

    def encode(self, obj:Any) -> bytes:
        """ Encode an object into JSON bytes data, handling contents with non-standard data types in self.default.
            An explicit encoder flag is required to keep non-ASCII Unicode characters intact. """
        return json.dumps(obj, ensure_ascii=False, default=self.default).encode(self.encoding)

    def default(self, obj:Any) -> JSONType:
        """ Convert arbitrary Python objects into JSON-compatible types using specially-named conversion methods. """
        type_name = type(obj).__name__
        try:
            meth = getattr(self, f"convert_{type_name}")
            return meth(obj)
        except Exception as e:
            raise TypeError(f"Could not encode object of type {type_name} into JSON.") from e

    def add_data_class(self, data_cls:type) -> None:
        """ Add a conversion method for a data class, whose instance attributes may be encoded
            directly into a JSON object. This uses vars(), so objects without a __dict__ are not allowed.
            For this to work, each attribute must contain either a JSON-compatible type or another data class.
            Since type information is not encoded, this conversion is strictly one-way. """
        setattr(self, f"convert_{data_cls.__name__}", vars)

    # Convert sets and frozensets into lists, which become JSON arrays.
    convert_set = list
    convert_frozenset = list
