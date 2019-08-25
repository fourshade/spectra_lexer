""" Module for formatting and displaying types and values of arbitrary Python objects. """

from functools import lru_cache
from io import TextIOWrapper
from itertools import islice

from .container import ContainerData


@lru_cache(maxsize=None)
class TypeParams:
    """ Contains row parameters for a data type. These are cached, so attributes may not be modified directly. """

    # Base data types to treat as atomic/indivisible. Attempting iteration on these is either wasteful or harmful.
    _ATOMIC_TYPES = {type(None), type(...),      # System singletons.
                     bool, int, float, complex,  # Guaranteed not iterable.
                     str, bytes, bytearray,      # Items are just characters; do not iterate over these.
                     range, slice,               # Items are just a pre-determined mathematical range.
                     filter, map, zip,           # Iteration is destructive.
                     TextIOWrapper}              # Iteration may crash the program if std streams are in use.

    _GRAPH_CONNECTIONS = {"└": "├",  # Replacement symbols when connecting to existing lines on a graph from the bottom.
                          "┴": "┼"}

    __slots__ = ("name", "mro_names", "graph", "is_atomic")

    def __init__(self, tp:type):
        self._add_names(tp)
        self._add_graph(tp)
        self.is_atomic = tp in self._ATOMIC_TYPES

    def _add_names(self, tp:type) -> None:
        """ A type's icon is chosen from keywords describing it in order from specific to general.
            For now, the icon choices are just the names of each type in the MRO in order. """
        self.name = tp.__name__
        self.mro_names = (*[cls.__name__ for cls in tp.__mro__],)

    def _add_graph(self, tp:type) -> None:
        """ Compute a string representation of a type's MRO using monospaced box characters. """
        connect_tbl = self._GRAPH_CONNECTIONS
        pos_by_cls = {}
        char_lines = []
        for n, cls in enumerate(tp.__mro__[::-1]):
            pos_by_cls[cls] = n
            new_line = []
            try:
                base_cols = [pos_by_cls[b] for b in cls.__bases__]
                m = base_cols[-1]
                new_line += "  " * m
                new_line += "──" * (n - m)
                for s in base_cols:
                    col = 2 * s
                    new_line[col] = "└" if s == m else "┴"
                    for line in char_lines[n-1:s:-1]:
                        char = line[col]
                        if char in connect_tbl:
                            line[col] = connect_tbl[char]
                            break
                        line[col] = "│"
            except Exception:
                if n:
                    new_line += "???"
            new_line += cls.__name__
            char_lines.append(new_line)
        self.graph = "\n".join(map("".join, char_lines))


class ValueParams:
    """ Special utility for computing display values of Python objects in a node tree. """

    MAX_LEN: int = 100        # Maximum string length for an object display.
    MAX_ITEMS: int = 6        # Maximum item count for a container display.
    PLACEHOLDER: str = '...'  # Replaces items past the item limit and deeper than the recursion limit.

    text: str              # Computed string for the object's value.
    is_meta: bool          # True if object is a subclass of type.
    is_exception: bool     # True if object is an exception (includes BaseExceptions).
    _levels_left: int = 2  # Recursion levels left before placeholder is used. Default setting is the maximum.

    def __init__(self, x:object):
        self.text = self._repr(x)
        self.is_meta = isinstance(x, type) and issubclass(x, type)
        self.is_exception = isinstance(x, BaseException)

    def _repr(self, x:object) -> str:
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
        return s

    def _repr_iterable(self, x, left:str, right:str, repr_fn=None) -> str:
        if not x:
            return repr(x)
        if self._levels_left <= 0:
            s = self.PLACEHOLDER
        else:
            maxsize = self.MAX_ITEMS
            self._levels_left -= 1
            items = map(repr_fn or self._repr, islice(x, maxsize))
            self._levels_left += 1
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
        return self._repr_iterable(x, '{', '}')

    def repr_frozenset(self, x:frozenset) -> str:
        return self._repr_iterable(x, 'frozenset({', '})')

    def repr_dict(self, x:dict) -> str:
        def item_repr(k, fn=self._repr):
            return f"{fn(k)}: {fn(x[k])}"
        return self._repr_iterable(x, '{', '}', repr_fn=item_repr)

    repr_mappingproxy = repr_dict


class RowData(dict):
    """ A tree row consisting of three items. """

    def __init__(self, obj:object, parent_data:dict=()):
        """ Gather row parameters from the object's parent container, type, value, and possible contents. """
        type_params = TypeParams(type(obj))
        value_params = ValueParams(obj)
        super().__init__(parent_data,
                         icon_choices=type_params.mro_names,
                         type_text=type_params.name,
                         type_tooltip=type_params.graph,
                         value_text=value_params.text)
        # Metaclasses show a special icon.
        if value_params.is_meta:
            self["icon_choices"] = ("__METATYPE__", *self["icon_choices"])
        # Exceptions are bright red in any container.
        if value_params.is_exception:
            self["color"] = (192, 0, 0)
        # Only allow container expansion for types where it is useful.
        # Expanding strings into a row for each character is a mess just waiting to happen.
        # (especially since each character is *also* a string...containing itself.)
        if not type_params.is_atomic:
            self.update(ContainerData(obj, self.__class__))
