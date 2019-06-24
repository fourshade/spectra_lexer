""" Module for auto-generated container classes with formats for specific objects. """

import builtins
import types
from types import FrameType

from .base import Container, if_hasattr, if_isinstance


class GeneratedContainer(Container):
    """ An immutable container that generates a dict and stores that instead of the original object. """

    color = (32, 32, 128)  # Auto-generated containers are blue.
    key_tooltip = value_tooltip = "Auto-generated item; cannot edit."

    def __init__(self, obj):
        d = self._gen_dict(obj)
        super().__init__(d)

    def _gen_dict(self, obj) -> dict:
        return {}


@if_hasattr("__class__")
class ClassContainer(GeneratedContainer):
    """ A container that displays the class hierarchy for custom classes. """

    _EXCLUDED_CLASSES: set = {i for m in (builtins, types) for i in vars(m).values() if isinstance(i, type)}

    def _gen_dict(self, obj) -> dict:
        """ Allow class access if the object has an instance dict, or metaclass access if the object *is* a class.
            The main exception is type, which is its own class and would expand indefinitely.
            Others include built-in types which provide next to nothing useful in their attr listings. """
        if hasattr(obj, "__dict__"):
            return {cls.__name__: cls for cls in type(obj).__mro__ if cls not in self._EXCLUDED_CLASSES}
        return {}


@if_isinstance(BaseException)
class ExceptionContainer(GeneratedContainer):
    """ A container for an exception object to show details about the entire stack. """

    def _gen_dict(self, obj:BaseException) -> dict:
        d = {f"arg{i}": v for i, v in enumerate(obj.args)}
        for k in ("__cause__", "__context__"):
            v = getattr(obj, k)
            if v is not None:
                d[k] = v
        tb = obj.__traceback__
        while tb is not None:
            f = tb.tb_frame
            d[f'{f.f_code.co_name}:{tb.tb_lineno}'] = f
            tb = tb.tb_next
        return d


@if_isinstance(FrameType)
class FrameContainer(GeneratedContainer):
    """ Shows all information about a stack frame. """

    def _gen_dict(self, obj:FrameType) -> dict:
        code = obj.f_code
        return dict(name=code.co_name, filename=code.co_filename, lineno=obj.f_lineno,
                    globals=obj.f_globals, locals=obj.f_locals, code=code)
