from reprlib import Repr


class NodeRepr(Repr):
    """ Special repr utility for displaying values of various Python containers in a node tree. """

    def __init__(self):
        super().__init__()
        self.maxlevel = 2
        self.maxother = 50
        self.maxstring = 100

    def repr_instance(self, obj, level) -> str:
        """ Simpler version of reprlib.repr for arbitrary objects that doesn't cut out in the middle. """
        try:
            s = repr(obj)
        except Exception:
            s = None
        if s is None or len(s) > self.maxother:
            return '<%s object at %#x>' % (obj.__class__.__name__, id(obj))
        return s
