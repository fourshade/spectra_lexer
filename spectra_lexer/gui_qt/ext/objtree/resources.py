""" Contains resource classes for interactive tree operations. These are expensive to create and probably unused
    most of the time, so they are computed only on dialog open. """

import sys

from spectra_lexer.codec import XMLElement


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

    def __init__(self, components:list, **kwargs):
        """ Make a root dict with packages containing all modules, the first level of components, and any keywords.
            Each component is indexed by its class's module path in a nested package dict.
            Do not include the root package name. Anything in a 'base' module represents its entire package. """
        d = package()
        for cmp in components:
            ks = type(cmp).__module__.split(".")
            if len(ks) > 1 and ks[-1] in (ks[-2], "base"):
                ks.pop()
            d[".".join(ks[1:])] = cmp
        super().__init__(d.nested(), **kwargs)
        self["modules"] = package(sys.modules).nested()


class IconPackage(XMLElement):
    """ Subclass for handling icon data from SVG files. """

    def encode_all(self):
        """ From a root SVG icon resource, encode individual icon elements for each type. """
        defs = [e for e in self if e.tag == "defs"]
        for elem in self.recurse_children():
            # Elements with at least one type alias are valid icons.
            types = elem.get("spectra_types")
            if types:
                # Yield an encoded copy of this node with only the defs and the chosen element.
                icon = self.__class__(*defs, elem, **self)
                icon.tag = self.tag
                yield types.split(), icon.encode()

    def recurse_children(self):
        """ Yield this element, then recursively yield elements from its children, depth-first. """
        yield self
        for elem in self:
            yield from elem.recurse_children()
