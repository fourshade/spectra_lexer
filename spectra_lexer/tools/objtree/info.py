from reprlib import Repr


class TypeDict(dict):
    """ Holds a cache of display information related to object types. Only computes new information when required. """

    def __call__(self, obj:object):
        tp = type(obj)
        if tp not in self:
            self.compute(tp)
        return self[tp]

    def compute(self, tp:type) -> None:
        """ Subclasses must compute the required information and save it under the type's key. """
        raise NotImplementedError


class IconFinder(TypeDict):
    """ Returns the closest available icon to the object's type. """

    def compute(self, tp:type) -> None:
        """ Search for icons matching each type in the MRO by both reference and name.
            Once a match is found (`object` must always match), save it under each type traversed. """
        for i, cls in enumerate(tp.__mro__):
            icon = self.get(cls) or self.get(cls.__name__)
            if icon is not None:
                self.update(dict.fromkeys(tp.__mro__[:i+1], icon))
                return


class MroTree(TypeDict):
    """ Displays the MRO tree for object types. """

    def compute(self, tp:type) -> None:
        """ Compute and cache a string representation of a type's MRO. """
        self[tp] = "\n".join([("--" * i) + cls.__name__ for i, cls in enumerate(tp.__mro__[::-1])])


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
