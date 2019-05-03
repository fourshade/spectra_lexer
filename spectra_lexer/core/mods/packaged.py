from collections import defaultdict

from .base import ComponentModMeta
from .command import CommandMod
from spectra_lexer.types import package


class PackagedModMeta(ComponentModMeta):

    _PACKAGED_CLASSES: dict = {}

    def __new__(mcs, name, bases, dct, package_key=None, **kwargs):
        """ Register each subclass under an additional key if part of the debug package. """
        cls = super().__new__(mcs, name, bases, dct, **kwargs)
        if package_key is not None:
            mcs._PACKAGED_CLASSES[package_key] = cls
        return cls

    @classmethod
    def all_packages(mcs) -> dict:
        """ Return a dict with packages from all packaged mod classes. """
        return {mk: cls.make_package() for mk, cls in sorted(mcs._PACKAGED_CLASSES.items())}


class PackagedMod(CommandMod, metaclass=PackagedModMeta):

    pkg_key: str

    @classmethod
    def make_package(cls) -> package:
        """ Add all mods of type <cls> with their package key for every owner class. """
        d = defaultdict(list)
        for m in cls.lookup_mods():
            d[m.pkg_key].append(m)
        return package(d)


class CommandDef(PackagedMod, key="on", package_key="commands"):
    """ Descriptor for recording and binding component class instances to command functions. """

    def __init__(self, key:str):
        self.cmd_key = self.pkg_key = key
