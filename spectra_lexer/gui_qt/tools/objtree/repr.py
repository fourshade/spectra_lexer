from itertools import islice


class ValueRepr:
    """ Special repr utility for displaying values of various Python objects in a node tree. """

    maxlevel = 2
    maxlen = 100
    maxitems = 6
    placeholder = '...'

    _level = 0

    def __call__(self, x:object) -> str:
        self._level = self.maxlevel
        return self.repr(x)

    def repr(self, x:object) -> str:
        self._level -= 1
        tp = type(x)
        tp_name = tp.__name__
        try:
            if tp.__repr__ is object.__repr__:
                s = _repr_default(x, tp_name)
            else:
                meth_name = f'repr_{tp_name}'
                if ' ' in tp_name:
                    meth_name = meth_name.replace(' ', '_')
                s = getattr(self, meth_name, repr)(x)
        except Exception:
            s = _repr_default(x, tp_name)
        if len(s) > self.maxlen:
            s = s[:self.maxlen - 3] + self.placeholder
        self._level += 1
        return s

    def _repr_iterable(self, x, left:str, right:str, repr_fn=None) -> str:
        if self._level < 0:
            s = self.placeholder
        else:
            maxsize = self.maxitems
            items = map(repr_fn or self.repr, islice(x, maxsize))
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
        return self._repr_iterable(x, '{', '}') if x else 'set()'

    def repr_frozenset(self, x:frozenset) -> str:
        return self._repr_iterable(x, 'frozenset({', '})') if x else 'frozenset()'

    def repr_dict(self, x:dict) -> str:
        def item_repr(k, fn=self.repr):
            return f"{fn(k)}: {fn(x[k])}"
        return self._repr_iterable(x, '{', '}', item_repr)

    repr_mappingproxy = repr_dict


def _repr_default(x:object, tp_name:str) -> str:
    return f'<{tp_name} at 0x{id(x):0>8X}>'
