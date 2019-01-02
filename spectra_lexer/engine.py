from typing import Any, Hashable, Dict

from spectra_lexer import SpectraComponent
from spectra_lexer.base import control_decorator, SpectraCommand

on = control_decorator()              # Most basic decorator; calls the command with nothing else expected.
pipe = control_decorator("send_key")  # Decorator to mark a command to pipe its return value to another command.
respond_to = control_decorator()        # like @on, but can return the value to caller.
fork = control_decorator("send_key")  # like @pipe, but can also return the value to caller.


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

    _command_getters: Dict[SpectraComponent, callable]  # Mapping getter methods for every component's commands.

    def __init__(self):
        self._command_getters = {}

    def connect(self, component:SpectraComponent) -> None:
        """ Connect the specified component to the engine. """
        self._command_getters[component] = component.commands().get
        component.set_engine_callbacks(self.call, self.send)

    def disconnect(self, component:SpectraComponent) -> None:
        """ Disconnect the specified component from the engine. """
        del self._command_getters[component]
        component.set_engine_callbacks()

    def _lookup_commands(self, cmd_key):
        return list(filter(None, [m(cmd_key) for m in self._command_getters.values()]))

    def call(self, cmd_key:Hashable, *args, **kwargs) -> Any:
        """ Call <command> on the last valid target with the given arguments and return the value. """
        commands = self._lookup_commands(cmd_key)
        if commands:
            return self.execute(commands[-1], *args, **kwargs)

    def send(self, cmd_key:Hashable, *args, **kwargs) -> None:
        """ Call <command> on each valid target with the given arguments and return nothing. """
        for c in self._lookup_commands(cmd_key):
            self.execute(c, *args, **kwargs)

    def execute(self, command:SpectraCommand, *args, **kwargs) -> Any:
        try:
            value = command.func(*args, **kwargs)
            return self.dispatch(value, **command.kwargs)
        except Exception as e:
            # Call exception handler (newest first). If it fails, re-raise.
            if not self.call("handle_exception", e):
                raise e

    def dispatch(self, value, send_key=None, unless=None, unpack=False, **cmd_kwargs) -> Any:
        if send_key is not None and value is not unless:
            if unpack:
                self.send(send_key, *value, **cmd_kwargs)
            else:
                self.send(send_key, value, **cmd_kwargs)
        return value
