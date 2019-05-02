class package(dict):
    """ Class used for packaging components, markers, and modules under string keys.
        Splits all keys on <DELIM> and build a nested dict arranged in a hierarchy based on these splits.
        If one key is a prefix of another, it may occupy a slot needed for another level of dicts.
        If this happens, that value will be moved one level deeper to the key <ROOT_NAME>. """

    DELIM: str = "."
    ROOT_NAME: str = "__init__"

    __slots__ = ()

    @classmethod
    def nested(cls, *args, **kwargs):
        self = cls()
        self.update_nested(dict(*args, **kwargs))
        return self

    def update_nested(self, d):
        items_iter = getattr(d, "items", d.__iter__)()
        for k, v in items_iter:
            self.set_nested(k, v)

    def set_nested(self, k, v):
        root_name = self.ROOT_NAME
        *first, last = k.split(self.DELIM)
        for i in first:
            if i not in self:
                self[i] = package()
            elif not isinstance(self[i], package):
                self[i] = package({root_name: self[i]})
            self = self[i]
        if last not in self or not isinstance(self[last], package):
            self[last] = v
        else:
            self[last][root_name] = v
