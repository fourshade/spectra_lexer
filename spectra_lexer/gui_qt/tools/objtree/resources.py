import sys

from spectra_lexer.types.codec import XMLElement
from spectra_lexer.utils import recurse


class package(dict):
    """ Class for packaging objects and modules under string keys in a nested dict. """

    __slots__ = ()

    def nested(self, delim:str=".", root_key:str="__init__"):
        """ Split all keys on <delim> and nest package dicts in a hierarchy based on these splits.
            If one key is a prefix of another, it may occupy a slot needed for another level of dicts.
            If this happens, move the value one level deeper under <root_key>. """
        cls = self.__class__
        pkg = cls()
        for k, v in self.items():
            d = pkg
            *first, last = k.split(delim)
            for i in first:
                if i not in d:
                    d[i] = cls()
                elif not isinstance(d[i], cls):
                    d[i] = cls({root_key: d[i]})
                d = d[i]
            if last not in d or not isinstance(d[last], cls):
                d[last] = v
            else:
                d[last][root_key] = v
        return pkg


class RootDict(dict):

    __slots__ = ()

    def __init__(self, components:list):
        """ Make a root dict with packages containing all modules and the first level of components.
            Each component is indexed by its class's module path in a nested package dict.
            Do not include the root package name. Anything in a 'base' module represents its entire package. """
        d = package()
        for cmp in components:
            ks = type(cmp).__module__.split(".")
            if ks[-1] == "base":
                ks.pop()
            d[".".join(ks[1:])] = cmp
        super().__init__(d.nested())
        self["modules"] = package(sys.modules).nested()


class IconData:

    _data: list

    def __init__(self, icon_data:bytes):
        """ Decode the SVG icon resources and create individual icon elements for each type. """
        self._data = []
        root = XMLElement.decode(icon_data)
        defs = [e for e in root if e.tag == "defs"]
        for elem in recurse(root):
            # Elements with at least one type alias are valid icons.
            types = elem.get("spectra_types")
            if types:
                # Make an encoded copy of the root node with only its defs and this element.
                icon = XMLElement(*defs, elem, **root)
                icon.tag = root.tag
                self._data.append((types.split(), icon.encode()))

    def __iter__(self):
        return iter(self._data)
