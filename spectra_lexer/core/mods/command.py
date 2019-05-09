from typing import Callable, Dict, Iterable, List, Tuple

from .base import ComponentMod, MainMod
from .package import DebugPackageMod
from spectra_lexer.types.dict import multidict


class CommandMod(ComponentMod):
    """ Descriptor for recording and binding component class methods to command keys.
        All commands with the same key are executed in sequence with the same args. """

    cmd_key: str

    @classmethod
    def bind_all(cls, cmp:object) -> List[Tuple[str, Callable]]:
        """ Bind a component to callable commands from its class hierarchy and return the commands. """
        return [(m.cmd_key, m.bind(cmp)) for m in cls.lookup_cmp_mods(cmp)]

    def bind(self, cmp:object) -> Callable:
        """ Bind a component instance to the command and return a final callable. """
        return getattr(cmp, self._attr)


class CommandDef(MainMod, DebugPackageMod, CommandMod):

    KEY = "on"
    DEBUG_KEY = "commands"

    pkg_key: str

    def __init__(self, key:str):
        self.cmd_key = self.pkg_key = key

    @classmethod
    def package_items(cls, components:Iterable[object]) -> Dict[str, CommandMod]:
        """ Return a list of commands for each key over every component class. """
        return multidict([(m.pkg_key, m) for cmp in components for m in cls.lookup(cmp)])
