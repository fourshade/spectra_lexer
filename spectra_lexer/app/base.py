from collections import defaultdict
from typing import Dict, List

from spectra_lexer import Component


class Application:
    """
    Base application engine class for the Spectra program. Routes messages and data structures between
    all constituent components. Has mappings for every command to a list of registered functions along
    with where to send the return value. Components and commands should not change after initialization.
    """

    components: List[Component]  # List of all connected components.
    _commands: Dict[str, list]   # Dict of commands from all components combined into a list for each key.
    _rlevel: int = 0             # Level of re-entrancy for exceptions, 0 = top of stack.

    def __init__(self, *cls_or_mod):
        """ Create instances of all unique component classes in modules that do not share an inheritance line. """
        classes = [cls for m in cls_or_mod for cls in (m, *vars(m).values())
                   if isinstance(cls, type) and issubclass(cls, Component)]
        # Only instantiate the most derived class of each line. Position in the list determines command execution order.
        self.components = [cls() for cls in classes if sum(issubclass(other, cls) for other in classes) == 1]
        # Add commands and set callbacks for all components.
        self._commands = defaultdict(list)
        for c in self.components:
            c.engine_connect(self.call)
            for key, cmd in c.engine_commands():
                self._commands[key].append(cmd)

    def start(self, *args) -> object:
        """ Run the general lifecycle of the application. """
        options = self.get_options()
        self.set_options(**options)
        self.load_resources()
        return self.run(*args)

    def get_options(self) -> dict:
        """ Gather startup options from all components. Also add a component section for debug purposes. """
        options = defaultdict(list, components=self.components)
        for c in self.components:
            for src, opt in c.engine_options():
                options[src].append(opt)
        return options

    def set_options(self, **options) -> None:
        """ Process options such as command line arguments from sys.argv. Engine calls are not allowed yet. """
        self.call("set_options", **options)

    def load_resources(self) -> None:
        """ Open engine communications and start resource loading. """
        self.call("load_resources")

    def run(self, *args) -> object:
        """ After everything else is ready, a primary task may be run. It may return a single value to main().
            A batch operation can run until complete, or a GUI event loop can run indefinitely. """
        raise NotImplementedError

    def call(self, key:str, *args, **kwargs) -> object:
        """ Run all commands under this key (if any) and return the last value. """
        value = None
        for cmp, attr, cmd_args, cmd_kwargs in self._commands[key]:
            with self:
                value = getattr(cmp, attr)(*args, **kwargs)
            # If there's a follow-up command to run and the output value wasn't None, run it with that value.
            if value is not None and cmd_args:
                # Normal tuples (not subclasses) will be automatically unpacked into the next command.
                next_args = value if type(value) is tuple else (value,)
                self.call(*cmd_args, *next_args, **cmd_kwargs)
        return value

    def __enter__(self) -> None:
        """ Re-entrant context manager; used to check exceptions with a custom handler. """
        self._rlevel += 1

    def __exit__(self, exc_type:type, exc_value:BaseException, traceback:object) -> bool:
        """ The caller may depend on exceptions, so don't catch them here unless this is the top level. """
        self._rlevel -= 1
        return exc_value is not None and self._rlevel <= 0 and self.call("new_exception", exc_value)
