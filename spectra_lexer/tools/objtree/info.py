from reprlib import Repr


class TypeDict(dict):
    """ Holds a cache of display information related to object types. Only computes new information when required. """

    def __call__(self, obj:object):
        return self[type(obj)]


class IconFinder(TypeDict):
    """ Returns the closest available icon ID to the object's type. """

    def __init__(self, ids:list):
        """ Each element ID without a starting underline is a valid icon.
            The types each icon corresponds to are separated by + characters. """
        super().__init__({tp_name: k for k in ids if not k.startswith("_") for tp_name in k.split("+")})

    def __missing__(self, tp:type) -> str:
        """ Search for icon IDs matching each type in the MRO by both reference and name.
            Once a match is found (`object` must always match), save it under each type traversed. """
        for i, cls in enumerate(tp.__mro__):
            icon_id = self.get(cls) or self.get(cls.__name__)
            if icon_id is not None:
                self.update(dict.fromkeys(tp.__mro__[:i+1], icon_id))
                return icon_id


class MroTree(TypeDict):
    """ Displays the MRO tree for object types. """

    def __missing__(self, tp:type) -> str:
        """ Compute and cache a string representation of a type's MRO. """
        s = self[tp] = "\n".join([("--" * i) + cls.__name__ for i, cls in enumerate(tp.__mro__[::-1])])
        return s


class NodeRepr(Repr):
    """ Special repr utility for displaying values of various Python objects in a node tree. """

    def __init__(self):
        super().__init__()
        self.maxlevel = 2
        self.maxother = 50
        self.maxstring = 100

    def repr_instance(self, obj:object, level:int) -> str:
        """ Simpler version of reprlib.repr for arbitrary objects that doesn't cut out in the middle. """
        try:
            s = repr(obj)
        except Exception:
            s = None
        if s is None or len(s) > self.maxother:
            return '<%s object at %#x>' % (obj.__class__.__name__, id(obj))
        return s
