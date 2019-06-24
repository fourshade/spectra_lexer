""" --------------------------GENERAL PURPOSE CLASSES---------------------------
    These classes are used to modify the behavior of attributes and methods on other classes.
    Some are used like functions or other low-level constructs, so their names are all lowercase. """

# A robust dummy object. Always returns itself through any chain of attribute lookups, subscriptions, and calls.
_DUMMY_METHODS = ["__getattr__", "__getitem__", "__call__"]
dummy = type("dummy", (), dict.fromkeys(_DUMMY_METHODS, lambda self, *a, **k: self))()
