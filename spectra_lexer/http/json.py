""" Module for JSON codecs adapted for HTTP data transmission. """

from json import JSONDecodeError, JSONDecoder, JSONEncoder
from typing import NoReturn, Union

from .service import BinaryDataProcessor

JSONType = Union[None, bool, int, float, str, tuple, list, dict]  # Python types supported by json module.


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


class CustomJSONEncoder(JSONEncoder):
    """ Encodes arbitrary Python data types into JSON using named conversion methods and/or vars(). """

    def default(self, obj:object) -> JSONType:
        """ Convert a non-standard Python object into a JSON-compatible type if possible.
            The object must either:
            - match a conversion method on this encoder by exact type name, or
            - possess a __dict__ whose values are all JSON-compatible types or other such objects recursively.
            Since type information is not encoded, this conversion is strictly one-way. """
        type_name = type(obj).__name__
        try:
            method = getattr(self, f'convert_{type_name}', vars)
            return method(obj)
        except Exception as e:
            raise TypeError(f'Could not encode object of type "{type_name}" into JSON.') from e

    # Ranges, sets, and frozensets can be converted into lists with no consequences.
    convert_range = list
    convert_set = list
    convert_frozenset = list


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
    """ Interface for an application that accepts and returns JSON-compatible dictionaries at its boundary. """

    def run(self, d:dict) -> dict:
        raise NotImplementedError


class JSONObjectProcessor(BinaryDataProcessor):
    """ Application wrapper that converts JSON objects to/from binary data. """

    output_type = "application/json"

    def __init__(self, app:JSONApplication, codec:JSONCodec=None) -> None:
        self._app = app                     # Wrapped application.
        self._codec = codec or JSONCodec()  # Converter between encoded JSON objects and Python dictionaries.

    def process(self, data:bytes) -> bytes:
        """ Decode the input data, call the application, and return the encoded output data. """
        obj_in = self._codec.decode(data)
        if not isinstance(obj_in, dict):
            raise TypeError('Top level of input data must be a JSON object.')
        obj_out = self._app.run(obj_in)
        if not isinstance(obj_out, dict):
            raise TypeError('Output must be a dictionary.')
        return self._codec.encode(obj_out)
