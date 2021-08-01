""" Module for JSON codecs adapted for HTTP data transmission. """

from json import JSONDecodeError, JSONDecoder, JSONEncoder
from typing import Dict, List, NoReturn, Tuple, Union

from .service import BinaryDataProcessor

# Spec for Python types directly supported by json module.
JSONType = Union[None, bool, int, float, str, 'JSONTuple', 'JSONList', 'JSONDict']
JSONTuple = Tuple[JSONType, ...]
JSONList = List[JSONType]
JSONDict = Dict[str, JSONType]


class JSONStruct(JSONDict):
    """ Struct/record type designed for serialization as a JSON object.
        To do so without a custom parser, it must be a dictionary (if only internally).
        Subclasses form a schema by adding annotations to specify required and optional fields. """

    def __init__(self, **kwargs:JSONType) -> None:
        """ Check annotations for required fields and copy default values for optional ones. """
        super().__init__(kwargs)
        for k in self.__annotations__:
            if k not in self:
                try:
                    self[k] = getattr(self, k)
                except AttributeError:
                    raise TypeError(f'Missing required field "{k}"') from None
        self.__dict__ = self


class JSONRestrictionError(JSONDecodeError):
    """ Raised if user-provided JSON data is too large or complex to decode. """


class RestrictedJSONDecoder(JSONDecoder):
    """ Checks untrusted JSON data for restrictions before decoding. """

    def __init__(self, *, size_limit:int=None, obj_limit:int=None, arr_limit:int=None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._size_limit = size_limit  # Limit, if any, on total size of JSON data in characters.
        self._obj_limit = obj_limit    # Limit, if any, on total number of objects (recursion included).
        self._arr_limit = arr_limit    # Limit, if any, on total number of arrays (recursion included).

    def _reject(self, s:str, reason:str) -> NoReturn:
        raise JSONRestrictionError(f'JSON rejected - {reason}.', s, 0)

    def decode(self, s:str, **kwargs) -> JSONType:
        """ Validate and decode an untrusted JSON string. """
        if self._size_limit is not None and len(s) > self._size_limit:
            self._reject(s, "too large")
        # The Python JSON parser is fast, but dumb. It does naive recursion on containers.
        # The stack can be overwhelmed by a long sequence of '{' and/or '[' characters. Do not let this happen.
        if self._obj_limit is not None and s.count("{") > self._obj_limit:
            self._reject(s, "too many objects")
        if self._arr_limit is not None and s.count("[") > self._arr_limit:
            self._reject(s, "too many arrays")
        return super().decode(s, **kwargs)


class JSONCodec:
    """ Combines a JSON decoder and encoder for binary data using the same character encoding. """

    def __init__(self, decoder:JSONDecoder=None, encoder:JSONEncoder=None, *, encoding='utf-8') -> None:
        self._decoder = decoder or JSONDecoder()  # JSON decoder: decode(str) -> JSONType.
        self._encoder = encoder or JSONEncoder()  # JSON encoder: encode(JSONType) -> str.
        self._encoding = encoding                 # Pretty much has to be UTF-8.

    def decode(self, data:bytes) -> JSONType:
        """ Decode raw input data as a JSON object and return it. """
        str_in = data.decode(self._encoding)
        return self._decoder.decode(str_in)

    def encode(self, obj:JSONType) -> bytes:
        """ Encode an output object as JSON and return the raw output data. """
        str_out = self._encoder.encode(obj)
        return str_out.encode(self._encoding)


class JSONApplication:
    """ Interface for an application that accepts and returns JSON-compatible types at its boundary. """

    def run(self, **kwargs:JSONType) -> JSONType:
        raise NotImplementedError


class JSONObjectProcessor(BinaryDataProcessor):
    """ Application wrapper that converts JSON to/from binary data. """

    output_type = "application/json"

    def __init__(self, app:JSONApplication, codec:JSONCodec=None) -> None:
        self._app = app                     # Wrapped application.
        self._codec = codec or JSONCodec()  # Converter between encoded JSON objects and Python dictionaries.

    def process(self, data:bytes) -> bytes:
        """ Decode the input data, call the application, and return the encoded output data. """
        obj_in = self._codec.decode(data)
        if not isinstance(obj_in, dict):
            raise TypeError('Top level of input data must be a JSON object.')
        obj_out = self._app.run(**obj_in)
        return self._codec.encode(obj_out)
