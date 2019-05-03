from typing import Callable, List, Tuple

from .base import ComponentMod


class CommandMod(ComponentMod):
    """ For subclasses, the command key given in __init__ may be modified.
        All commands with the same name are executed in sequence with the same args. """

    cmd_key: str

    @classmethod
    def bind_all(cls, cmp:object) -> List[Tuple[str, Callable]]:
        """ Bind a component to callable commands from its class hierarchy and return the commands. """
        return [(m.cmd_key, m.bind(cmp)) for m in cls.lookup_by_owner(type(cmp))]

    def bind(self, cmp:object) -> Callable:
        """ Bind a component instance to the command and return a final callable. """
        return getattr(cmp, self._attr)
