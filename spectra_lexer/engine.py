from collections import defaultdict
from typing import Any, Callable, DefaultDict, List

from spectra_lexer import SpectraComponent


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

    _command_map: DefaultDict[str, List[Callable]]  # Mapping of every command to a list of callback structures.

    def __init__(self, *components:SpectraComponent, **kwargs):
        """ Construct the engine, add built-in commands, connect the root components to it,
            and start it with the keyword arguments (sent by command line). """
        self._command_map = defaultdict(list)
        self._command_map["new_status"] = [print]
        for c in components:
            self.connect(c)
        self("start", **kwargs)

    def connect(self, component:SpectraComponent) -> None:
        """ Connect the specified component to the engine, adding its commands to the signal table. """
        # Add all commands it handles with their callback methods and set the engine callback itself.
        for (command, meth) in component.commands():
            self._command_map[command].append(meth)
        component.set_engine_callback(self)

    def __call__(self, command:str, *args, default:Any=None, **kwargs) -> Any:
        """ Call <command> on each valid target with the given arguments and return the last value. """
        # TODO: Find a way to propagate all unhandled exceptions to this level, including ones from Qt.
        value = default
        for func in self._command_map[command]:
            try:
                value = func(*args, **kwargs)
            except Exception as e:
                # Try exception handlers (newest first) until one returns True.
                # any() will short-circuit when this happens. If it never does, re-raise.
                if not any(handler(e) for handler in reversed(self._command_map["handle_exception"])):
                    raise
        return value
