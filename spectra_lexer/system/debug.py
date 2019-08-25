import inspect
import pkgutil
import sys
from typing import Callable


class xhelp:
    """ You asked for help on help, didn't you? Boredom has claimed yet another victim.
        This object overrides the builtin 'help', which breaks custom Python consoles. """

    _HELP_SECTIONS = [lambda x: [f"OBJECT - {x!r}"],
                      lambda x: [f"  TYPE - {type(x).__name__}"],
                      lambda x: ["----------SIGNATURE----------",
                                 inspect.signature(x)],
                      lambda x: ["----------ATTRIBUTES----------",
                                 ', '.join([k for k in dir(x) if not k.startswith('_')]) or "None"],
                      lambda x: ["-------------INFO-------------",
                                 *map(str.lstrip, str(x.__doc__).splitlines())]]

    def __call__(self, *args:object, write:Callable=print) -> None:
        """ Write each help section that doesn't raise an exception, in order. """
        if not args:
            write(self)
        for obj in args:
            write("")
            for fn in self._HELP_SECTIONS:
                try:
                    for line in fn(obj):
                        write(line)
                except Exception:
                    # Arbitrary objects may raise arbitrary exceptions. Just skip sections that don't behave.
                    continue
            write("")

    def __repr__(self) -> str:
        return "Type help(object) for auto-generated help on any Python object."


class package(dict):
    """ Class for packaging objects and modules under string keys in a nested dict. """

    __slots__ = ()

    def nested(self, delim:str=".", root_key:str="__init__"):
        """ Split all keys on <delim> and nest package dicts in a hierarchy based on these splits.
            If one key is a prefix of another, it may occupy a slot needed for another level of dicts.
            If this happens, move the value one level deeper under <root_key>. """
        cls = self.__class__
        pkg = cls()
        for k, v in self.items():
            d = pkg
            *first, last = k.split(delim)
            for i in first:
                if i not in d:
                    d[i] = cls()
                elif not isinstance(d[i], cls):
                    d[i] = cls({root_key: d[i]})
                d = d[i]
            if last not in d or not isinstance(d[last], cls):
                d[last] = v
            else:
                d[last][root_key] = v
        return pkg


class AutoImporter(package):
    """ Interpreter namespace dict that functions as a copy of __builtins__ with extra features.
        It automatically tries to import missing modules any time code would otherwise throw a NameError. """

    __slots__ = ()

    def __missing__(self, k:str):
        """ Try to import missing modules before raising a KeyError (which becomes a NameError).
            If successful, attempt to import submodules recursively. """
        try:
            module = self[k] = __import__(k, self, locals(), [])
        except Exception:
            raise KeyError(k)
        try:
            for finder, name, ispkg in pkgutil.walk_packages(module.__path__, f'{k}.'):
                __import__(name, self, locals(), [])
        except Exception:
            pass
        return module


class DebugDict(dict):
    """ Debug namespace dict that automatically imports top-level modules for convenience. """

    __slots__ = ()

    def __init__(self, *args, **kwargs):
        """ Auto-import tends to pollute namespaces with tons of garbage. We don't need that at the top level.
            The actual auto-import dict is hidden as __builtins__, and is tried only after the main dict fails. """
        super().__init__(*args, **kwargs)
        # The AutoImporter constructor will copy the real global builtins dict; it won't be corrupted.
        self["__builtins__"] = AutoImporter(__builtins__, help=xhelp())
        self["modules"] = package(sys.modules).nested()

    def add_component(self, key:str, obj:object):
        """ Mark the object as a component and add it to the namespace. """
        obj.__class__.__COMPONENT__ = True
        self[key] = obj
