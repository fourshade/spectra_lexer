from collections import defaultdict
from typing import Dict, Hashable

from spectra_lexer import Component


class Application:
    """
    Base application engine class for the Spectra program. Routes messages and data structures between
    all constituent components. Has mappings for every command to a list of registered functions along
    with where to send the return value. Components and commands should not change after initialization.
    Since all execution state is kept within the call stack, multiple threads may run without conflict.
    """

    components: Dict[str, Component]  # Dict of all connected components by role. Primarily exists for introspection.
    _commands: Dict[Hashable, list]   # Dict of commands from all components combined into a list for each key.
    _rlevel: int = 0                  # Level of re-entrancy, 0 = top of stack.

    def __init__(self, *cmp_iter:object):
        """ Gather all component classes in order from base to derived classes.
            Instantiate only one per role. Later components override earlier ones. """
        self.components = {role: cls() for role, cls in _get_component_classes(list(cmp_iter)).items()}
        self._commands = defaultdict(list)
        # Add commands and set callbacks for all components.
        for c in self.components.values():
            for (key, cmd) in c.engine_commands():
                self._commands[key].append(cmd)
            c.engine_connect(self.call)

    def start(self, **opts) -> None:
        """ Parse command line arguments from sys.argv and keyword options given by subclasses or by main(). """
        self.call("cmdline_parse", **opts)
        # Add the app and its components to the keyword options and send the start signal.
        self.call("start", app=self, components=self.components, **opts)

    def call(self, key:Hashable, *args, **kwargs) -> object:
        """ Run all commands under this key (if any) and return the last value. """
        value = None
        for func, next_key, cmd_kwargs in self._commands[key]:
            with self:
                value = func(*args, **kwargs)
            # If there's a follow-up command to run and the output value wasn't None, run it with that value.
            if value is not None and next_key is not None:
                # Normal tuples (not subclasses) will be automatically unpacked into the next command.
                next_args = value if type(value) is tuple else (value,)
                self.call(next_key, *next_args, **cmd_kwargs)
        return value

    def __enter__(self) -> None:
        """ Re-entrant context manager; used to check exceptions with a custom handler. """
        self._rlevel += 1

    def __exit__(self, exc_type:type, exc_value:BaseException, traceback:object) -> bool:
        """ The caller may depend on exceptions, so don't catch them here unless this is the top level. """
        self._rlevel -= 1
        return exc_value is not None and not self._rlevel and self.call("new_exception", exc_value)


def _get_component_classes(items:list, depth:int=2) -> dict:
    """ Get all unique component subclasses in a list of arbitrary items along with their roles.
        If any of the items are modules, get classes from their namespaces as well, down to the given depth. """
    for _ in range(depth):
        # Test only the namespace attributes which are public (not underscored).
        items += [v for item in items if hasattr(item, "__package__")
                  for k, v in vars(item).items() if not k.startswith("_")]
    return {item.ROLE: item for item in items if hasattr(item, "ROLE") and item is not Component}
