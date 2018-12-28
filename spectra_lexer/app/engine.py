from collections import defaultdict
from typing import Any, Dict, Hashable

from spectra_lexer import SpectraComponent
from spectra_lexer.utils import nop


class SpectraEngine:
    """
    Master component communications class for the Spectra program. Routes messages and data structures between
    the application, the GUI, and all other constituent components.

    The program itself is conceptually divided into parts that form a pipeline:
        File/input - The most basic operation of the lexer requires a set of rules that map steno keys to letters,
        and these must be loaded from disk. The first step on startup after connecting the components is for the
        lexer to ask for a dictionary of rules, and this module will load these from the built-in directory.

        Search/input - Translations for the program to parse have to come from somewhere, and usually it's a JSON
        dictionary loaded from outside. The search component handles all search functionality and sends queries
        to the lexer at certain points when the old information is ready to be overwritten by new information.

        Plover/input - Translations and search dictionaries may also come from Plover when activated as a plugin.
        Strokes from Plover are handled independently of search results; the output window will display the last
        translation no matter where it came from.

        Lexer/processing - A translation consists of a series of strokes mapped to an English word, and it is the
        lexer's job to match pieces of each using a dictionary of rules it has loaded from storage. All rules handling
        is done by the lexer component, including parsing them from JSON files on disk and converting them back
        if need be. All results are handed off to the output component, which decides their fate.

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

    _commands: Dict[Hashable, list]  # Mapping getter methods for every component's commands.
    _exception_callback: callable    # Application-provided callback for exception handling.

    def __init__(self, on_exception=nop):
        self._commands = defaultdict(list)
        self._exception_callback = on_exception

    def connect(self, component:SpectraComponent) -> None:
        """ Add the specified component's commands to the engine and set its callback. """
        for (k, c) in component.commands():
            self._commands[k].append(c)
        component.set_engine_callback(self.call)

    def call(self, cmd_key:Hashable, *args, **kwargs) -> Any:
        """ Top-level method for engine command calls. Used directly by app and components. Contains exception handler.
            If an uncaught exception occurs anywhere, either let the application callback handle it or re-raise. """
        try:
            return self._call(cmd_key, *args, **kwargs)
        except Exception as e:
            if not self._exception_callback(e):
                raise e

    def _call(self, cmd_key:Hashable, *args, **kwargs) -> Any:
        """ Call a command on each valid component (in reverse order of connection) with the given arguments.
            Each target may dispatch its result somewhere else and/or return it to the caller.
            If a target is required to return a value, stop the loop there and return it. """
        for c in reversed(self._commands[cmd_key]):
            value = c.func(*args, **kwargs)
            if self._dispatch(value, **c.kwargs):
                return value

    def _dispatch(self, value, next_key=None, unpack=False, ret=False, **cmd_kwargs) -> bool:
        """ If a command is marked to pipe its output to another command (and it isn't None), start a new call
            cycle with that command. Return True if the command must (also) return the output to its caller. """
        if next_key is not None and value is not None:
            if unpack:
                self._call(next_key, *value, **cmd_kwargs)
            else:
                self._call(next_key, value, **cmd_kwargs)
        return ret
