""" Contains classes specifically for handling certain use cases of HTTP methods. """

import json
from mimetypes import MimeTypes
import os
from typing import Callable, Dict

from .request import HTTPRequest
from .response import HTTPResponse, HTTPError


class HTTPMethodHandler:
    """ Abstract base class for an HTTP method handler that creates a response object from a request object. """

    def __call__(self, request:HTTPRequest) -> HTTPResponse:
        raise NotImplementedError


class HTTPMethodTable(HTTPMethodHandler):
    """ Master method handler that redirects requests to other handlers based on method type. """

    _handlers: Dict[str, HTTPMethodHandler]  # Table of HTTP method handlers.

    def __init__(self, **handlers):
        self._handlers = handlers

    def __call__(self, request:HTTPRequest) -> HTTPResponse:
        """ Route HTTP requests by method. Handlers must be completely thread safe. """
        method = request.method.upper()
        handler = self._handlers.get(method)
        if handler is None:
            raise HTTPError.NOT_IMPLEMENTED(method)
        return handler(request)


class HTTPFileGetter(HTTPMethodHandler):
    """ Handles methods specific to file retrieval (generally using GET and HEAD requests). """

    _directory: str       # Root directory for public HTTP file requests.
    _head: bool           # We must skip any content body if the command is HEAD.
    _index_filename: str  # When a directory path is accessed, redirect to this landing page inside it.
    _types: MimeTypes     # Called to find MIME types for files based on their paths.

    def __init__(self, directory:str=None, *, head:bool=False, index_filename:str= "index.html"):
        self._directory = directory or os.getcwd()
        self._head = head
        self._index_filename = index_filename
        self._types = MimeTypes()

    def __call__(self, request:HTTPRequest) -> HTTPResponse:
        """ Common file-serving code for GET and HEAD commands. """
        uri_path = request.path
        file_path = self._translate_path(uri_path)
        try:
            return self._file_response(file_path, request)
        except OSError:
            raise HTTPError.NOT_FOUND(uri_path)

    def _file_response(self, file_path:str, request:HTTPRequest) -> HTTPResponse:
        """ Open a file and send it in the response if it exists and was not cached recently. """
        with open(file_path, 'rb') as f:
            fs = os.fstat(f.fileno())
            mtime = fs.st_mtime
            if not request.modified_since(mtime):
                return HTTPResponse.NOT_MODIFIED()
            ctype = self._types.guess_type(file_path)[0]
            return HTTPResponse.OK(modified=mtime, ctype=ctype, content=f.read(), head=self._head)

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
            file_path = os.path.join(file_path, self._index_filename)
        return file_path


class HTTPJSONProcessor(HTTPMethodHandler):
    """ Handles methods specific to JSON processing (generally using POST requests). """

    _processor: Callable  # External callback to process JSON data.
    _size_limit: int      # Limit on total size of JSON data in bytes.
    _char_limits: tuple   # Limits on special JSON characters.

    def __init__(self, processor:Callable, *, size_limit:int=100000, char_limits:tuple=((b"{", 20),(b"[", 20))):
        self._processor = processor
        self._size_limit = size_limit
        self._char_limits = char_limits

    def __call__(self, request:HTTPRequest) -> HTTPResponse:
        """ Process JSON and query data obtained from a client.
            If successful, encode any relevant changes to JSON and send them back to the client. """
        data = request.content
        self._validate(data)
        s = data.decode('utf-8')
        obj_in = self._loads(s)
        obj_out = self._process(obj_in, request.path, request.query)
        if obj_out is None:
            raise HTTPError.INTERNAL_SERVER_ERROR()
        s = self._dumps(obj_out)
        data = s.encode('utf-8')
        return HTTPResponse.OK(ctype="application/json", content=data)

    def _validate(self, data:bytes) -> None:
        """ Validate incoming JSON data from a client. This data could contain ANYTHING...beware! """
        if len(data) > self._size_limit:
            raise ValueError("Data payload too large.")
        # The JSON parser is fast, but dumb. It does naive recursion on containers.
        # The stack can be overwhelmed by a long sequence of '{' and/or '[' characters. Do not let this happen.
        for c, limit in self._char_limits:
            if data.count(c) > limit:
                raise ValueError("Too many containers.")

    _loads = staticmethod(json.loads)

    def _process(self, obj_in:object, path:str, query:dict) -> object:
        """ Process the object by itself. Subclasses must override to use the path and/or query parameters. """
        return self._processor(obj_in)

    _dumps = staticmethod(json.dumps)
