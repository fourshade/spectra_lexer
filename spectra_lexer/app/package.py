from collections import defaultdict


class package(dict):
    """ Class used for packaging debug components and modules. """

    __slots__ = ()

    def __init__(self, *args, _delim:str=".", _root_name:str= "__init__", **kwargs):
        """ Split all keys on <_delim> and build a nested dict arranged in a hierarchy based on these splits.
            If one key is a prefix of another, it may occupy a slot needed for another level of dicts.
            If this happens, that value will be moved one level deeper to the key <_root_name>. """
        super().__init__()
        d = defaultdict(dict)
        for k, v in dict(*args, **kwargs).items():
            first, *rest = k.split(_delim, 1)
            d[first][rest[0] if rest else _root_name] = v
        for k, sect in d.items():
            if len(sect) == 1:
                self[k], = sect.values()
            else:
                n = package(sect, _delim=_delim, _root_name=_root_name)
                if len(n) == 1:
                    (rest, v), = n.items()
                    self[k + _delim + rest] = v
                else:
                    self[k] = n
