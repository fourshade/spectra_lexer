from collections import defaultdict
from typing import Dict

from spectra_lexer import Component


class Application:
    """
    Base application engine class for the Spectra program. Routes messages and data structures between
    all constituent components. Has mappings for every command to a list of registered functions along
    with where to send the return value. Components and commands should not change after initialization.
    Since all execution state is kept within the call stack, multiple threads may run without conflict.
    """

    components: Dict[str, Component]  # Dict of all connected components by role. Primarily exists for introspection.
    _commands: Dict[str, list]        # Dict of commands from all components combined into a list for each key.
    _rlevel: int = 0                  # Level of re-entrancy, 0 = top of stack.

    def __init__(self, *cls_mod_iter:object):
        """ Connect all unique components and component classes in order, including those in modules. """
        iters = [vars(item).values() if hasattr(item, "__package__") else [item] for item in cls_mod_iter]
        # Only one component is allowed per role. Later components in iteration order override earlier ones.
        filtered = {cmp.ROLE: cmp for it in iters for cmp in it if hasattr(cmp, "ROLE")}
        # Component objects may be used directly, but classes must be instantiated.
        self.components = {role: (cls() if isinstance(cls, type) else cls) for role, cls in filtered.items()}
        # Add commands and set callbacks for all components.
        self._commands = defaultdict(list)
        for c in self.components.values():
            c.engine_connect(self.call)
            for (func, key, *params) in c.engine_commands():
                # Bind all class command functions to the instance and save the finished tuples.
                self._commands[key].append((func.__get__(c, type(c)), *params))

    def start(self, **opts) -> None:
        """ Parse command line arguments from sys.argv. """
        self.call("cmdline_parse")
        # Add the app and its components to the keyword options given by main() and send the start signal.
        self.call("start", app=self, components=self.components, **opts)

    def call(self, key:str, *args, **kwargs) -> object:
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
