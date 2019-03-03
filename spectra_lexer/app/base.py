from collections import defaultdict
from typing import Dict, Hashable, Generator, Iterable

from spectra_lexer import Component


class Application:
    """
    Base application engine class for the Spectra program. Routes messages and data structures between
    all constituent components. Has mappings for every command to a list of registered functions along
    with where to send the return value. Components and commands should not change after initialization.
    Since all execution state is kept within the call stack, multiple threads may run without conflict.
    """

    components: Dict[str, Component]  # Dict of all connected components by role.
    commands: Dict[Hashable, list]    # Dict of commands from all components combined into a list for each key.

    def __init__(self, *cmp_iter:object):
        """ Gather all component classes in order from base to derived classes.
            Instantiate only one per role. Later components override earlier ones. """
        classes = dict(_get_component_classes(cmp_iter))
        self.components = {role: cls() for role, cls in classes.items()}
        # Add commands and set callbacks for all components.
        self.commands = defaultdict(list)
        for c in self.components.values():
            for (key, cmd) in c.engine_commands():
                self.commands[key].append(cmd)
            c.engine_connect(self.call)

    def start(self, **opts) -> None:
        """ Parse command line arguments from sys.argv and keyword options given by subclasses or by main(). """
        self.call("cmdline_parse", **opts)
        # Add the app and its components to the keyword options and send the start signal.
        self.call("start", app=self, components=self.components, **opts)

    def call(self, key:Hashable, *args, is_top:bool=True, **kwargs) -> object:
        """ Re-entrant method for engine calls. Checks exceptions with a custom handler. """
        try:
            value = None
            # Run all commands under this key (if any) and return the last value.
            for func, next_key, cmd_kwargs in self.commands[key]:
                value = func(*args, **kwargs)
                # If there's a follow-up command to run and the output value wasn't None, run it with that value.
                if value is not None and next_key is not None:
                    # Normal tuples (not subclasses) will be automatically unpacked into the next command.
                    next_args = value if type(value) is tuple else (value,)
                    self.call(next_key, *next_args, is_top=False, **cmd_kwargs)
            return value
        except Exception as e:
            # The caller may want to catch this exception, so don't catch it here unless this is the top level.
            if not is_top or not self.call("new_exception", e):
                raise


def _get_component_classes(items:Iterable, parent:str="") -> Generator:
    """ Yield all component subclasses in an iterable of arbitrary items along with their roles.
        If any of the items are child modules, yield from their namespaces recursively. """
    for item in items:
        if isinstance(item, type) and issubclass(item, Component) and item is not Component:
            yield item.ROLE, item
        elif hasattr(item, "__package__") and item.__package__.startswith(parent):
            yield from _get_component_classes(vars(item).values(), item.__package__)
