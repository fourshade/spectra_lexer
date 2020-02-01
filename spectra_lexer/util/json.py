""" Module for special JSON codecs. """

from json import JSONDecodeError, JSONDecoder, JSONEncoder
from typing import Union

JSONType = Union[None, bool, int, float, str, tuple, list, dict]  # Python types supported by json module.


class CSONDecoder(JSONDecoder):
    """ Reads non-standard JSON with full-line comments (CSON = commented JSON). """

    def __init__(self, *, comment_prefix="#", **kwargs) -> None:
        super().__init__(**kwargs)
        self._comment_prefix = comment_prefix  # Prefix for comment lines.

    def decode(self, s:str, *args, **kwargs) -> JSONType:
        """ Decode a non-standard JSON string with full-line comments.
            JSON doesn't care about leading or trailing whitespace, so strip every line first. """
        lines = s.split("\n")
        stripped_line_iter = map(str.strip, lines)
        data_lines = [line for line in stripped_line_iter
                      if line and not line.startswith(self._comment_prefix)]
        s = "\n".join(data_lines)
        return super().decode(s, *args, **kwargs)


class JSONRestrictionError(JSONDecodeError):
    """ Raised if user-provided JSON data is too large or complex. """


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
        # The JSON parser is fast, but dumb. It does naive recursion on containers.
        # The stack can be overwhelmed by a long sequence of '{' and/or '[' characters. Do not let this happen.
        if self._obj_limit is not None and s.count("{") > self._obj_limit:
            self._reject(s, "too many objects")
        if self._arr_limit is not None and s.count("[") > self._arr_limit:
            self._reject(s, "too many arrays")
        return super().decode(s, *args, **kwargs)

    def _reject(self, s:str, reason:str) -> None:
        raise JSONRestrictionError(f"JSON rejected - {reason}.", s, 0)


class CustomJSONEncoder(JSONEncoder):
    """ Encodes non-standard Python data types using specially-named conversion methods. """

    def default(self, obj:object) -> JSONType:
        """ Convert an arbitrary Python object into a JSON-compatible type. """
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

    # Convert ranges, sets, and frozensets into lists, which become JSON arrays.
    convert_range = list
    convert_set = list
    convert_frozenset = list
