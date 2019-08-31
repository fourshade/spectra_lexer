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


class HTTPMethodTable(HTTPRequestHandler):
    """ Master request handler that redirects requests to other handlers based on method type. """

    def __init__(self, **handlers:HTTPRequestHandler) -> None:
        self._handlers = handlers  # Table of HTTP method handlers.

    def __call__(self, request:HTTPRequest) -> HTTPResponse:
        """ Route HTTP requests by method. Handlers must be completely thread safe. """
        method = request.method.upper()
        handler = self._handlers.get(method)
        if handler is None:
            raise HTTPError.NOT_IMPLEMENTED(method)
        return handler(request)


class HTTPFileGetter(HTTPRequestHandler):
    """ Handles requests specific to file retrieval (generally using GET and HEAD methods). """

    def __init__(self, directory:str, index_filename:str="index.html") -> None:
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


class HTTPDataProcessor(HTTPRequestHandler):
    """ Abstract class; handles requests specific to data processing (generally using the POST method). """

    CTYPE: str = "text/html"  # MIME content type for outgoing data.

    def __call__(self, request:HTTPRequest) -> HTTPResponse:
        """ Process content, path, and query data obtained from a client.
            If successful, encode the returned object and send it back to the client. """
        try:
            data_in = request.content
            obj_in = self.decode(data_in)
            obj_out = self.process(obj_in, request.path, request.query)
            data_out = self.encode(obj_out)
            return HTTPResponse.OK(ctype=self.CTYPE, content=data_out)
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


class HTTPJSONProcessor(HTTPDataProcessor):
    """ Abstract class; decodes a JSON object from HTTP content, processes it, and returns a JSON-encoded result. """

    ENCODING = 'utf-8'
    CTYPE = "application/json"

    def __init__(self, *, size_limit:int=100000, char_limits:tuple=((b"{", 20), (b"[", 20))):
        self._size_limit = size_limit    # Limit on total size of JSON data in bytes.
        self._char_limits = char_limits  # Limits on special JSON characters.

    def decode(self, data:bytes) -> object:
        """ Validate and decode incoming JSON data from a client. """
        if len(data) > self._size_limit:
            raise ValueError("JSON rejected - data payload too large.")
        # The JSON parser is fast, but dumb. It does naive recursion on containers.
        # The stack can be overwhelmed by a long sequence of '{' and/or '[' characters. Do not let this happen.
        for c, limit in self._char_limits:
            if data.count(c) > limit:
                raise ValueError("JSON rejected - too many containers.")
        return json.loads(data)

    def encode(self, obj:object) -> bytes:
        """ Encode an object into JSON bytes data, handling contents with non-standard data types in self.default.
            An explicit encoder flag is required to keep non-ASCII Unicode characters intact. """
        return json.dumps(obj, ensure_ascii=False, default=self.default).encode(self.ENCODING)

    def default(self, obj:Any) -> Union[str, list]:
        """ Convert bytes objects into strings and other arbitrary iterables into lists. """
        if isinstance(obj, (bytes, bytearray)):
            return obj.decode(self.ENCODING)
        elif hasattr(obj, "__iter__"):
            return list(obj)
        raise TypeError(f"Could not encode object of type {type(obj)} into JSON.")
