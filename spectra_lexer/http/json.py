""" Module for JSON codecs adapted for HTTP data transmission. """

from json import JSONDecodeError, JSONDecoder, JSONEncoder
from typing import Callable, Union

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

    def decode(self, s:str, *args, **kwargs) -> JSONType:
        """ Validate and decode an untrusted JSON string. """
        if self._size_limit is not None and len(s) > self._size_limit:
            self._reject(s, "too large")
        # The Python JSON parser is fast, but dumb. It does naive recursion on containers.
        # The stack can be overwhelmed by a long sequence of '{' and/or '[' characters. Do not let this happen.
        if self._obj_limit is not None and s.count("{") > self._obj_limit:
            self._reject(s, "too many objects")
        if self._arr_limit is not None and s.count("[") > self._arr_limit:
            self._reject(s, "too many arrays")
        return super().decode(s, *args, **kwargs)

    def _reject(self, s:str, reason:str) -> None:
        raise JSONRestrictionError(f"JSON rejected - {reason}.", s, 0)


class CustomJSONEncoder(JSONEncoder):
    """ Encodes arbitrary Python data types into JSON using specially-named conversion methods. """

    def default(self, obj:object) -> JSONType:
        """ Convert a non-standard Python object into a JSON-compatible type if possible.
            There must be a conversion method that matches the object's exact type name. """
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
        type_name = data_cls.__name__
        setattr(self, f"convert_{type_name}", vars)

    # Ranges, sets, and frozensets can be converted into lists with no consequences.
    convert_range = list
    convert_set = list
    convert_frozenset = list


class JSONBinaryWrapper:
    """ Binary wrapper for a function that processes keyword arguments and returns a JSON-encodable type. """

    def __init__(self, func:Callable, *, decoder:JSONDecoder=None, encoder:JSONEncoder=None, encoding='utf-8') -> None:
        self._func = func                         # Wrapped function:  __call__(**kwargs) -> <output_type>
        self._decoder = decoder or JSONDecoder()  # JSON decoder:      decode(str) -> dict.
        self._encoder = encoder or JSONEncoder()  # JSON encoder:      encode(<output_type>) -> str.
        self._encoding = encoding                 # Pretty much has to be UTF-8.

    def __call__(self, data:bytes) -> bytes:
        """ Decode raw input data as a JSON object and call the function with its properties as keyword arguments.
            Encode the function's output as JSON and return the raw output data. """
        str_in = data.decode(self._encoding)
        obj_in = self._decoder.decode(str_in)
        if not isinstance(obj_in, dict):
            raise TypeError('Top level of JSON input data must be an object.')
        obj_out = self._func(**obj_in)
        str_out = self._encoder.encode(obj_out)
        data_out = str_out.encode(self._encoding)
        return data_out
