""" Package for the Python console suite, including GUI-specific terminal implementations. """

import code
import sys

BANNER = f"Spectra Console - Python {sys.version}"


def introspect(obj:object, *, include_private=True) -> int:
    """ Run a Python console to introspect <obj> using the standard streams. """
    filter_prefix = "__" if include_private else "_"
    namespace = {k: getattr(obj, k) for k in dir(obj) if not k.startswith(filter_prefix)}
    code.interact(banner=BANNER, local=namespace, exitmsg="")
    return 0
