""" Module for formatting and displaying types and values of arbitrary Python objects. """

from functools import lru_cache
from itertools import islice
from typing import Callable, Iterable, Tuple


@lru_cache(maxsize=None)
class TypeParams:
    """ Contains display parameters for an object type. Most types have lots of instances, so these are cached. """

    _GRAPH_CONNECTIONS = {"└": "├",  # Replacement symbols when connecting to existing lines on a graph from the bottom.
                          "┴": "┼"}

    __slots__ = ("name", "mro_names", "graph")

    def __init__(self, tp:type) -> None:
        """ A type's icon is chosen from keywords describing it in order from specific to general.
            For now, the icon choices are just the names of each type in the MRO in order. """
        self.name = tp.__name__
        self.mro_names = (*[cls.__name__ for cls in tp.__mro__],)
        self.graph = self._draw_graph(tp)

    def _draw_graph(self, tp:type) -> str:
        """ Compute and return a string representation of a type's MRO using monospaced box characters. """
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
        return "\n".join(map("".join, char_lines))


class ValueRepr:
    """ Computes string values of Python objects for display in a node tree. """

    def __init__(self, max_len:int=100, max_items:int=6, max_levels:int=2, placeholder:str='...') -> None:
        self.max_len = max_len          # Maximum string length for an object display.
        self.max_items = max_items      # Maximum item count for a container display.
        self.max_levels = max_levels    # Maximum recursion levels before placeholder is used.
        self.placeholder = placeholder  # Replaces items past the item limit and deeper than the recursion limit.
        self._levels_left = 0           # Recursion levels left in current run.

    def repr(self, x:object) -> str:
        """ Compute and return a string for the value of object <x>. """
        self._levels_left = self.max_levels
        return self._repr(x)

    def _repr(self, x:object) -> str:
        """ If we have a custom method for this object type, call it, otherwise use a default repr. """
        tp = type(x)
        tp_name = tp.__name__
        try:
            # If there is no __repr__ defined, use our default in the except rather than object.__repr__
            if tp.__repr__ is object.__repr__:
                raise Exception()
            meth_name = f'repr_{tp_name}'
            if ' ' in tp_name:
                meth_name = meth_name.replace(' ', '_')
            meth = getattr(self, meth_name, repr)
            s = meth(x)
        except Exception:
            s = f'<{tp_name} at 0x{id(x):0>8X}>'
        if len(s) > self.max_len:
            s = s[:self.max_len - 3] + self.placeholder
        return s

    def _repr_iterable(self, x, left:str, right:str, repr_fn=None) -> str:
        if not x:
            return repr(x)
        if self._levels_left <= 0:
            s = self.placeholder
        else:
            maxsize = self.max_items
            self._levels_left -= 1
            items = map(repr_fn or self._repr, islice(x, maxsize))
            self._levels_left += 1
            if len(x) > maxsize:
                items = [*items, self.placeholder]
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


class DebugData:
    """ A structure used to fully describe an object for debug purposes. """

    VALUE_REPR = ValueRepr().repr

    color: Tuple[int, int, int] = (0, 0, 0)
    key_text: str = "undefined"
    key_tooltip: str = ""
    key_edit: Callable = None
    child_data = None
    type_text: str = "undefined"
    type_graph: str = ""
    item_count: int = None
    value_text: str = "undefined"
    value_tooltip: str = ""
    value_edit: Callable = None
    icon_choices: Iterable[str] = ()

    def add_params(self, obj:object) -> None:
        """ Gather and add data related to the structure of an object by itself (not including its contents). """
        type_params = TypeParams(type(obj))
        self.type_text = type_params.name
        self.type_graph = type_params.graph
        self.value_text = self.VALUE_REPR(obj)
        # Metaclasses show a special icon.
        icons = type_params.mro_names
        if isinstance(obj, type) and issubclass(obj, type):
            icons = ("__METATYPE__", *icons)
        self.icon_choices = icons
        # Exceptions are bright red in any container.
        if isinstance(obj, BaseException):
            self.color = (192, 0, 0)
