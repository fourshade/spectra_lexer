""" Contains useful types for introspection and/or interactive interpreter operations. """

from functools import partial, update_wrapper
from typing import Callable


class AttrRedirector(list):
    """ Context manager that temporarily overwrites a number of attributes on a target object, then restores them.
        Only works on objects with a __dict__. The usual case is redirecting streams and hooks from the sys module. """

    def __init__(self, target:object, **attrs):
        """ We usually have specific literal attributes to redirect, so **keywords are best. """
        super().__init__([vars(target), attrs])

    def __exit__(self, *args) -> None:
        """ Switch the attributes on both dicts. This operation is symmetrical and works for __enter__ as well. """
        d, attrs = self
        for a in attrs:
            d[a], attrs[a] = attrs[a], d[a]

    __enter__ = __exit__


class HelpWrapper(partial):
    """ A function wrapped to display helpful information on repr() and help(). """

    __help__: str  # String shown on repr() and in place of ordinary help.

    def __new__(cls, func:Callable, wrapped=None):
        """ Add help using the name, annotations, and/or docstring of the function (or another wrapper). """
        self = super().__new__(cls, func)
        update_wrapper(self, func if wrapped is None else wrapped)
        lines = [f"COMMAND: {self.__name__}", ""]
        if hasattr(self, "__annotations__"):
            params = dict(self.__annotations__)
            ret = params.pop("return", "<unknown>")
            p = "ACCEPTS - "
            if not params:
                lines.append(f"{p}no arguments")
            for k, cls in params.items():
                lines.append(f"{p}{k}: {_short_type_name(cls)}")
                p = " " * len(p)
            lines += ["", f"RETURNS -> {_short_type_name(ret)}", ""]
        if hasattr(self, "__doc__"):
            lines += map(str.lstrip, str(self.__doc__).splitlines())
        self.__help__ = "\n".join(lines)
        return self

    def __repr__(self) -> str:
        return self.__help__


def _short_type_name(cls:type) -> str:
    """ Return the name of a type without all the annoying prefixes on generic type aliases. """
    return getattr(cls, '__name__', str(cls)).replace("typing.","")


class xhelp:
    """ You asked for help on help, didn't you? Boredom has claimed yet another victim.
        This object overrides the builtin 'help', which breaks custom Python consoles. """

    _HELP_SECTIONS = [lambda x: f"OBJECT - {x!r}",
                      lambda x: f"  TYPE - {type(x).__name__}",
                      lambda x: f"----------ATTRIBUTES----------\n"
                                f"{', '.join(_public_attrs(x)) or None}",
                      lambda x: f"-------------INFO-------------\n"
                                f"{x.__doc__}"]

    def __call__(self, *args:object) -> None:
        if not args:
            print(self)
        for obj in args:
            print("")
            if hasattr(obj, "__help__"):
                print(obj.__help__)
            else:
                for fn in self._HELP_SECTIONS:
                    try:
                        print(fn(obj))
                    except (AttributeError, TypeError, ValueError):
                        continue
            print("")

    def __repr__(self) -> str:
        return "Type help(object) for auto-generated help on any Python object."


def _public_attrs(obj:object) -> list:
    """ Return the public (non-underscore) attributes of <obj>. """
    return [k for k in dir(obj) if not k.startswith('_')]
