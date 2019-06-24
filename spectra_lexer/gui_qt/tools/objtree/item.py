""" Module for formatting and displaying types and values of arbitrary Python objects. """

from collections import defaultdict
from itertools import islice

from spectra_lexer.utils import memoize


class KeyItem(dict):
    """ Column 0 is the primary tree item with the key and icon. Possible icons are based on type. """

    def set_object(self, obj:object) -> None:
        self["icon_choices"] = self._mro_names(type(obj))

    @staticmethod
    @memoize
    def _mro_names(tp:type) -> tuple:
        """ Compute and cache a tuple of name strings for a type's MRO. """
        return (*[cls.__name__ for cls in tp.__mro__],)


class TypeItem(dict):
    """ Column 1 contains the type of object, item count, and/or a tooltip detailing the MRO. """

    def set_object(self, obj:object) -> None:
        tp = type(obj)
        self["text"] = tp.__name__
        self["tooltip"] = self._mro_tree(tp)

    @staticmethod
    @memoize
    def _mro_tree(tp:type) -> str:
        """ Compute and cache a string representation of a type's MRO. """
        levels = defaultdict(int)
        for cls in tp.__mro__[::-1]:
            levels[cls] = max([levels[b] for b in cls.__bases__], default=-1) + 1
        return "\n".join([("--" * i) + cls.__name__ for cls, i in levels.items()])


class ValueItem(dict):
    """ Column 2 contains the string value of the object. It may be edited if mutable. """

    MAX_LEVEL = 2
    MAX_LEN = 100
    MAX_ITEMS = 6
    PLACEHOLDER = '...'

    _level = 0

    def set_object(self, obj:object):
        self._level = self.MAX_LEVEL
        self["text"] = self.repr(obj)

    def repr(self, x:object) -> str:
        """ Special repr utility for displaying values of various Python objects in a node tree. """
        self._level -= 1
        tp = type(x)
        tp_name = tp.__name__
        try:
            if tp.__repr__ is object.__repr__:
                raise Exception()
            meth_name = f'repr_{tp_name}'
            if ' ' in tp_name:
                meth_name = meth_name.replace(' ', '_')
            s = getattr(self, meth_name, repr)(x)
        except Exception:
            s = f'<{tp_name} at 0x{id(x):0>8X}>'
        if len(s) > self.MAX_LEN:
            s = s[:self.MAX_LEN - 3] + self.PLACEHOLDER
        self._level += 1
        return s

    def _repr_iterable(self, x, left:str, right:str, repr_fn=None) -> str:
        if self._level < 0:
            s = self.PLACEHOLDER
        else:
            maxsize = self.MAX_ITEMS
            items = map(repr_fn or self.repr, islice(x, maxsize))
            if len(x) > maxsize:
                items = [*items, self.PLACEHOLDER]
            s = ', '.join(items)
        return f"{left}{s}{right}"

    def repr_tuple(self, x:tuple) -> str:
        s = self._repr_iterable(x, '(', ')')
        if len(x) == 1:
            s = s[:-1] + ",)"
        return s

    def repr_list(self, x:list) -> str:
        return self._repr_iterable(x, '[', ']')

    def repr_set(self, x:set) -> str:
        return self._repr_iterable(x, '{', '}') if x else 'set()'

    def repr_frozenset(self, x:frozenset) -> str:
        return self._repr_iterable(x, 'frozenset({', '})') if x else 'frozenset()'

    def repr_dict(self, x:dict) -> str:
        def item_repr(k, fn=self.repr):
            return f"{fn(k)}: {fn(x[k])}"
        return self._repr_iterable(x, '{', '}', item_repr)

    repr_mappingproxy = repr_dict
