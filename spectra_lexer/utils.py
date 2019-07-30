""" Module for generic utility functions that could be useful in many applications. """

import pkgutil


class AutoImporter(dict):
    """ Interpreter namespace dict that functions as a copy of __builtins__ with extra features.
        It automatically tries to import missing modules any time code would otherwise throw a NameError. """

    @classmethod
    def make_namespace(cls, *args, **kwargs) -> dict:
        """ Auto-import tends to pollute namespaces with tons of garbage. We don't need that at the top level.
            The actual auto-import dict is hidden as __builtins__, and is tried only after the main dict fails. """
        # The class constructor will copy the real global builtins dict; it won't be corrupted.
        return dict(*args, **kwargs, __builtins__=cls(__builtins__))

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
