from collections import defaultdict
from typing import Any, Callable, Dict, Iterable, List, Tuple


class Executor:
    """ Executes commands for an engine. Commands should not change after initialization. """

    _commands: Dict[str, List[Callable]]  # Holds command keys mapped to lists of callable commands.

    def __init__(self):
        self._commands = defaultdict(list)

    def add_commands(self, commands:Iterable[Tuple[str, Callable]]):
        """ Add commands by key. Commands cannot be disconnected. """
        for key, func in commands:
            self._commands[key].append(func)

    def __call__(self, *args, **kwargs) -> Any:
        """ Run a command and handle exceptions that make it back here.
            Qt will crash if exceptions propagate back to it; do not allow this under normal circumstances. """
        try:
            return self._exec(*args, **kwargs)
        except Exception as exc_value:
            # Exception handling is done, like anything else, by calling components.
            # Some apps may lock stderr while running, and a GUI can only print exceptions after setup.
            # Unhandled exceptions in an exception handler are fatal. They should return instead of raise.
            return self._exec("exception", exc_value)

    def _exec(self, key:str, *args, broadcast_depth:int=None, **kwargs) -> Any:
        """ Run all commands matching a key and return the last result. """
        value = None
        if broadcast_depth is not None:
            self._broadcast(key, args, kwargs, broadcast_depth)
        for func in self._commands[key]:
            value = func(*args, **kwargs)
        return value

    def _broadcast(self, key:str, args:tuple, kwargs:dict, depth:int=1) -> None:
        """ Broadcast commands require a pair iterable/dict as the first positional argument and cannot return a value.
            For each k:v pair, the key is a command to call with the value as the first argument. """
        depth -= 1
        pairs, *args = args
        if isinstance(pairs, dict):
            pairs = pairs.items()
        for k, v in pairs:
            k = f"{key}:{k}"
            v = v, *args
            if depth:
                self._broadcast(k, v, kwargs, depth)
            if self._commands[k]:
                self._exec(k, *v, **kwargs)
