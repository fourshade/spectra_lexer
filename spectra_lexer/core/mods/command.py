from typing import Callable, Iterable, List, Tuple

from .base import ComponentMod, MainMod
from .package import DebugPackageMod


class CommandMod(ComponentMod):
    """ Descriptor for recording and binding component class methods to command keys.
        All commands with the same key are executed in sequence with the same args. """

    cmd_key: str

    @classmethod
    def bind_all(cls, components:Iterable) -> List[Tuple[str, Callable]]:
        """ Bind each component to callable commands from its class hierarchy and yield the commands. """
        return [(m.cmd_key, m.bind(cmp)) for cmp in components for m in cls.lookup_cmp_mods(cmp)]

    def bind(self, cmp:object) -> Callable:
        """ Bind a component instance to the command and return a final key and callable. """
        return getattr(cmp, self._attr)


class CommandDef(MainMod, DebugPackageMod, CommandMod):

    KEY = "on"
    DEBUG_KEY = "commands"

    pkg_key: str

    def __init__(self, key:str):
        self.cmd_key = self.pkg_key = key

    @classmethod
    def package_items(cls, components:Iterable) -> Iterable:
        """ Return the last command (the one that will return a value) for each key over every component class. """
        return {m.pkg_key: m for cmp in components for m in cls.lookup(cmp)}
