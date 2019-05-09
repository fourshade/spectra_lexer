from typing import Callable

# None is everywhere in introspection. Sentinel values are needed here more than anywhere.
_SENTINEL = object()


class AttrRedirector:
    """ Context manager that temporarily overwrites a number of attributes on a target object, then restores them.
        Only works on objects with a __dict__. The usual case is redirecting streams and hooks from the sys module. """

    _saved = {}

    def __init__(self, target:object, **attrs):
        self._attrs = attrs
        self._target_dict = vars(target)

    def __enter__(self) -> None:
        self._saved = {a: self._target_dict[a] for a in self._attrs}
        self._target_dict.update(self._attrs)

    def __exit__(self, *args) -> None:
        self._target_dict.update(self._saved)


class WrappedCommand:
    """ A command object wrapped to display helpful information. """

    _call: Callable     # Engine callback of the *console*
    cmd_key: str = ""   # Command key; automatically obtained during wrapping.

    def __init__(self, f_list:list, engine_cb:Callable):
        """ Each command key may have more than one target function.
            Wrap this object as the first one and add help from each one with annotations and/or a docstring. """
        self._call = engine_cb
        if f_list:
            vars(self).update(vars(f_list[0]))
            lines = [f"COMMAND: {self.cmd_key}"]
            if len(f_list) > 1:
                lines.append("\n(Multiple targets)")
            for f in f_list:
                if hasattr(f, "__annotations__"):
                    params = dict(f.__annotations__)
                    ret = params.pop("return") if "return" in params else "<unknown>"
                    p = "\nACCEPTS - "
                    if not params:
                        lines.append(f"{p}no arguments")
                    for k, cls in params.items():
                        lines.append(f"{p}{k}: {_safe_get_name(cls)}")
                        p = " " * len(p)
                    lines.append(f"\nRETURNS -> {_safe_get_name(ret)}\n")
                if hasattr(f, "__doc__"):
                    lines.append(str(f.__doc__))
            self.__doc__ = "\n".join(lines)

    def __call__(self, *args, **kwargs):
        return self._call(self.cmd_key, *args, **kwargs)

    def __repr__(self) -> str:
        return self.__doc__


def _safe_get_name(cls:type):
    return getattr(cls, '__name__', cls)


class xhelp:
    """ Override for the builtin 'help', which breaks custom Python consoles. """

    def __call__(self, request=_SENTINEL) -> None:
        if request is _SENTINEL:
            print(repr(self))
        elif request is None:
            print("Mu.")
        else:
            try:
                print(request.__doc__)
            except AttributeError:
                print("No help available for this object.")

    def __repr__(self) -> str:
        return "Type help(object) for basic help on any Python object."
