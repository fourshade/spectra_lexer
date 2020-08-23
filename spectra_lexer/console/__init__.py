""" Package for the Python console suite, including GUI-specific terminal implementations. """

import code
import sys

BANNER = f"Spectra Console - Python {sys.version}"


class Proxy:
    """ Wrapper for setting attributes without affecting the original object. """

    def __init__(self, obj:object) -> None:
        self.__obj = obj

    def __getattr__(self, name:str):
        return getattr(self.__obj, name)


def override_code_excepthook():
    """ The code module handles exceptions rather stupidly based on the identity of sys.excepthook:
          - sys.excepthook is sys.__excepthook__: ignore it and print the traceback manually.
          - sys.excepthook is not sys.__excepthook__: call it and let exceptions out of the sandbox.
        This behavior can only be overridden by wrapping its global reference to sys. """
    if code.sys.excepthook is not sys.__excepthook__:
        code.sys = sys_proxy = Proxy(sys)
        sys_proxy.excepthook = sys.__excepthook__


def introspect(obj:object, *, include_private=True) -> int:
    """ Run a Python console to introspect <obj> using the standard streams. """
    filter_prefix = "__" if include_private else "_"
    namespace = {k: getattr(obj, k) for k in dir(obj) if not k.startswith(filter_prefix)}
    override_code_excepthook()
    code.interact(banner=BANNER, local=namespace, exitmsg="")
    return 0
