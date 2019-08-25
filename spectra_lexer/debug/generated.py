""" Module for auto-generated container classes with formats for specific objects. """

import builtins
import dis
import types
from types import CodeType, FrameType, FunctionType, MethodType
from typing import Any, Union

from .container import GeneratedContainer


class ClassContainer(GeneratedContainer):
    """ A container that displays the class hierarchy for custom classes. """

    _EXCLUDED_CLASSES: set = {i for m in (builtins, types) for i in vars(m).values() if isinstance(i, type)}

    def _gen_dict(self, obj:Any) -> dict:
        """ Allow class access if the object has an instance dict, or metaclass access if the object *is* a class.
            The main exception is type, which is its own class and would expand indefinitely.
            Others include built-in types which provide next to nothing useful in their attr listings. """
        return {cls.__name__: cls for cls in type(obj).__mro__ if cls not in self._EXCLUDED_CLASSES}


class ExceptionContainer(GeneratedContainer):
    """ A container for an exception object to show details about the entire stack. """

    def _gen_dict(self, exc:BaseException) -> dict:
        """ Add parent exceptions (cause/context), then each frame object going down the stack. """
        d = {f"arg{i}": v for i, v in enumerate(exc.args)}
        for k in ("__cause__", "__context__"):
            v = getattr(exc, k)
            if v is not None:
                d[k] = v
        tb = exc.__traceback__
        while tb is not None:
            f = tb.tb_frame
            d[f'{f.f_code.co_name}:{tb.tb_lineno}'] = f
            tb = tb.tb_next
        return d


class FrameContainer(GeneratedContainer):
    """ Shows all information about a stack frame. """

    def _gen_dict(self, f:FrameType) -> dict:
        """ Add only the most important inspectable information. """
        code = f.f_code
        return dict(name=code.co_name, filename=code.co_filename, lineno=f.f_lineno,
                    globals=f.f_globals, locals=f.f_locals, code=code)


class instruction:
    """ A bytecode instruction as displayed in the debug tree. Has a special icon. """

    __slots__ = ["_s"]

    def get(self, inst:dis.Instruction):
        """ Set an instruction's argument as a display string. If it is a code object, return that instead. """
        if hasattr(inst.argval, 'co_code'):
            return inst.argval
        if inst.arg is None:
            self._s = ""
        elif not inst.argrepr:
            self._s = f'{inst.arg}'
        else:
            self._s = f'{inst.arg} ({inst.argrepr})'
        return self

    def __repr__(self) -> str:
        return self._s


# Types known to consist of or contain inspectable bytecode.
_CODE_TYPES = (MethodType, FunctionType, CodeType, classmethod, staticmethod)


class CodeContainer(GeneratedContainer):
    """ Shows disassembly of a code object. """

    def _gen_dict(self, obj:Union[_CODE_TYPES]) -> dict:
        """ To display bytecode properly in the tree, make a special display object for each instruction found. """
        return {f'{inst.offset} {inst.opname}': instruction().get(inst) for inst in dis.get_instructions(obj)}


CONDITIONS = [(ClassContainer,     hasattr,    "__dict__"),
              (ExceptionContainer, isinstance, BaseException),
              (FrameContainer,     isinstance, FrameType),
              (CodeContainer,      isinstance, _CODE_TYPES)]
