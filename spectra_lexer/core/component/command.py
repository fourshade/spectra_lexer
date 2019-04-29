from collections import defaultdict
from functools import partial

from spectra_lexer.types import struct
from spectra_lexer.utils import nop


class Command(struct, _fields=["_key"], value=None):
    """ Descriptor for recording and executing component class commands. """

    _DICT = defaultdict(list)  # Data dict with component classes as keys and lists of command keys/instances as values.
    _deco = False

    def __call__(self, func):
        """ Used as a decorator, the function is called on change. """
        self.value = func
        self._deco = True
        return self

    def __set_name__(self, owner, name):
        """ Add to the data dicts, put the original value back, and chain the __set_name__ call if necessary. """
        self._DICT[owner].append(self)
        v = self.value
        setattr(owner, name, v)
        self._attr = name
        getattr(v, "__set_name__", nop)(owner, name)

    def bind(self, cmp):
        """ Bind a component instance to the command and return a final callable. """
        if self._deco:
            return getattr(cmp, self._attr)
        # If not used as a decorator, store the provided value on command call.
        return partial(setattr, cmp, self._attr)

    @classmethod
    def get_all(cls, cmp):
        """ Return each command with its key from the component's class hierarchy. """
        return [(m._cmd_key(), m) for m in cls._lookup(cmp)]

    def _cmd_key(self):
        return self._key

    @classmethod
    def _lookup(cls, cmp):
        """ Yield each command of this type from the component's class hierarchy. """
        for tp in type(cmp).__mro__:
            if tp in cls._DICT:
                yield from cls._DICT[tp]


class Resource(Command, desc=""):
    """ An external resource, configured before the application starts.  """

    @classmethod
    def get_all(cls, cmp):
        """ Return each resource with its natural key from the dict. """
        return [(m._key, m) for m in cls._lookup(cmp) if isinstance(m, cls)]

    def _cmd_key(self):
        """ The command always starts with 'res:'. """
        return f"res:{self._key}"
