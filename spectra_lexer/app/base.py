from collections import defaultdict
from typing import Dict, List

from spectra_lexer import Component


class Application:
    """
    Base application engine class for the Spectra program. Routes messages and data structures between
    all constituent components. Has mappings for every command to a list of registered functions along
    with where to send the return value. Components and commands should not change after initialization.
    Since all execution state is kept within the call stack, multiple threads may run without conflict.
    """

    components: List[Component]  # List of all connected components.
    _commands: Dict[str, list]   # Dict of commands from all components combined into a list for each key.
    _rlevel: int = 0             # Level of re-entrancy, 0 = top of stack.

    def __init__(self, *cls_mod_iter:object):
        """ Create instances of all unique component subclasses in order, including those in modules. """
        classes = [cls for i in cls_mod_iter for cls in (vars(i).values() if hasattr(i, "__package__") else [i])
                   if isinstance(cls, type) and issubclass(cls, Component) and cls is not Component]
        # Duplicate classes and classes with a direct inheritance relationship are not allowed.
        # Only instantiate the most derived class of each line. Remove duplicates entirely.
        self.components = [cls() for cls in classes if sum(issubclass(other, cls) for other in classes) == 1]
        self._commands = defaultdict(list)

    def start(self, **opts) -> object:
        """ Connect everything and run the general lifecycle of the application. """
        options = defaultdict(list)
        for c in self.components:
            # Add commands/options and set callbacks for all components.
            c.engine_connect(self.call)
            for key, (func, *params) in c.cmd_dict.items():
                # Bind all class command functions to the instance and save the finished tuples.
                self._commands[key].append((func.__get__(c, type(c)), *params))
            for (src, opt) in c.opt_list:
                # Add each option under the source command that handles it.
                options[src].append(opt)
        # Parse startup options such as command line arguments from sys.argv. This stage should be very quick.
        self.call("setup", options)
        # Add the app and its components to the keyword options given by main() and start resource loading.
        self.call("start", app=self, components=self.components, **opts)
        # After everything else is ready, a component may run an event loop indefinitely.
        # In batch mode, the main operation can run here. A single value may be returned to main().
        return self.call("run")

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
