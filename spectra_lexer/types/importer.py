from functools import partial


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
        """ Try to import missing modules before raising a KeyError (which becomes a NameError). """
        try:
            return auto_import(self, k, level=0)
        except AttributeError:
            pass
        raise KeyError(k)


def add_hook(module) -> None:
    """ If the module does not have __path__, it is not a package. There is nothing more to import from it.
        If the module has __getattr__, it may have been hooked already. Do not override it. """
    if hasattr(module, "__path__") and not hasattr(module, "__getattr__"):
        module.__getattr__ = partial(auto_import, module.__dict__)


def auto_import(d:dict, k:str, level=1):
    """ Try to import missing modules before raising a AttributeError.
        If successful, add a hook to let the module auto-import submodules with this function. """
    try:
        module = d[k] = __import__(k, d, locals(), [], level)
        add_hook(module)
        return module
    except Exception as e:
        # Anything can go wrong importing an arbitrary module. It may not even exist.
        # Even if it does, we can't predict what its code will do. In any case, just say we couldn't find it.
        raise AttributeError(f"No attribute or submodule named '{k}'") from e
