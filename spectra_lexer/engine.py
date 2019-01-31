from collections import defaultdict
from threading import Lock, RLock
from typing import Any, Dict, Hashable

from spectra_lexer import Component
from spectra_lexer.utils import nop


class SpectraEngine:
    """
    Master component communications class for the Spectra program. Routes messages and data structures between
    the application, the GUI, and all other constituent components.

    The program itself is conceptually divided into parts that form a pipeline:
        File/input - The most basic operation of the lexer requires a set of rules that map steno keys to letters,
        and these must be loaded from disk. The first step on startup after connecting the components is for this
        module to load the configuration from user data and rules from the built-in assets directory.

        Dict/input - After decoding each of the file formats from disk, every resource must be post-processed into
        its final form for use by the lexer and other components. In order to save any results, these structures must
        be convertable back into a raw disk format. The dict component handles all conversions in both directions.

        Search/input - Translations for the program to parse have to come from somewhere, and usually it's a JSON
        dictionary loaded from outside. The search component handles all search functionality and sends queries
        to the lexer at certain points when the old information is ready to be overwritten by new information.

        Plover/input - Translations and search dictionaries may also come from Plover when activated as a plugin.
        Strokes from Plover are handled independently of search results; the output window will display the last
        translation no matter where it came from.

        Lexer/processing - A translation consists of a series of strokes mapped to an English word, and it is
        the lexer's job to match pieces of each using a dictionary of rules it has loaded from storage. All rules
        handling is done by the lexer component, including parsing them into categories and matching them to pieces
        of translations. All results are handed off to the output component, which decides their fate.

        Display/output - The lexer provides its output (usually a rule constructed from user input) to this component
        which puts it in its final form for the GUI to display, including the text graph and the steno board layout
        diagram. This is strictly one-way - no information needs to pass back to the lexer or search from here.

        GUI - As the frontend for accepting user input and displaying lexer output, the GUI fits on top of all of
        the rest of the components. Interactions between the GUI and its components are mediated by an application
        layer, which is either above or below the GUI layer depending on the requirements for entry points.

    This class glues these components together, handling communication between each one as well as passing
    information from one stage of the pipeline to the next. Facilitating communication is *all* it should do;
    any actual software functionality should be implemented in one of the component classes.
    """

    _commands: Dict[Hashable, list]  # Mappings for every command to a list of registered functions/dispatchers.
    _exception_callback: callable    # Application-provided callback for exception handling.
    _lock: Lock                      # Counts levels of re-entrancy for engine calls.

    def __init__(self, on_exception:callable=nop):
        """ Initialize the engine's structures and exception handler (defaulting to none/re-raising automatically). """
        self._commands = defaultdict(list)
        self._exception_callback = on_exception
        self._lock = RLock()

    def connect(self, component:Component) -> None:
        """ Add the component's commands to the engine and set its callback. Commands execute in reverse order. """
        for (k, c) in component.engine_connect(self.call):
            self._commands[k].insert(0, c)

    def call(self, cmd_key:Hashable, *args, **kwargs) -> Any:
        """ Top-level method for engine calls. Checks exceptions with a custom handler.
            This method is re-entrant, so we need to track the re-entrancy level for exception handling. """
        try:
            # Add all commands to the stack. If there is at least one, run the first one and store the value.
            # If there is more than one, run them until the stack is exhausted, but still return the first value.
            stack = self._get_commands(cmd_key, args, kwargs)
            if stack:
                with self._lock:
                    value = self._run_next(stack)
                    while stack:
                        self._run_next(stack)
                    return value
        except Exception as e:
            # The caller may want to catch this exception, so don't catch it here unless this is the top level.
            # If this isn't the top level or the handler fails, re-raise.
            if self._lock._is_owned() or not self._exception_callback(e):
                raise

    def _run_next(self, stack:list) -> Any:
        """ Call the next valid command in order. The target may dispatch its result to another command.
            Each command added this way goes on the stack without returning. """
        func, dispatch, args, kwargs = stack.pop()
        value = func(*args, **kwargs)
        if value is not None and dispatch is not None:
            stack += self._get_commands(*dispatch(value))
        return value

    def _get_commands(self, cmd_key:Hashable, args:tuple, kwargs:dict) -> list:
        """ Make a list of commands from valid components in order under the given key with the arguments added. """
        return [(func, dispatch, args, kwargs) for (func, dispatch) in self._commands[cmd_key]]
