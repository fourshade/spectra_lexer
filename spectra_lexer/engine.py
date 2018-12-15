from collections import defaultdict
from typing import Dict, List

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

    _component_dict: Dict[SpectraComponent, dict]  # Dict mapping components to their command dicts, id hashed.
    _signal_map: Dict[str, List[tuple]]                  # Mapping of every command to a list of callback structures.

    def __init__(self, *components: SpectraComponent):
        """ Construct the engine and immediately add the specified components to it, if any. """
        self._component_dict = {}
        self._signal_map = defaultdict(list)
        self.connect(*components)

    def connect(self, *components: SpectraComponent, overwrite:bool=False) -> None:
        """ Connect all of the specified components to the engine, adding their commands to the signal table. """
        # If overwrite is True, disconnect any existing instances of the new components first.
        if overwrite:
            self._disconnect_same_type_as(*components)
        for c in components:
            if c in self._component_dict:
                raise KeyError("Component is already connected.")
            cmd_dict = c.engine_commands()
            self._component_dict[c] = cmd_dict
            self._modify_signal_map(c, cmd_dict, list_op="append")
            c.set_engine_callback(self.send)
            # If the component contains its own subcomponents, connect them recursively.
            subcomponents = c.engine_subcomponents()
            if subcomponents:
                self.connect(*subcomponents, overwrite=overwrite)

    def disconnect(self, *components: SpectraComponent) -> None:
        """ Disconnect all of the specified components, removing all dict entries and signal callbacks. """
        for c in components:
            # If the component contains its own subcomponents, disconnect them recursively.
            subcomponents = c.engine_subcomponents()
            if subcomponents:
                self.disconnect(*subcomponents)
            cmd_dict = self._component_dict.get(c)
            if c is None:
                raise KeyError("Component is not connected.")
            c.remove_engine_callback()
            self._modify_signal_map(c, cmd_dict, list_op="remove")
            del self._component_dict[c]

    def _disconnect_same_type_as(self, *components: SpectraComponent) -> None:
        """ Disconnect all instances of the same type as the specified components. """
        overwrite_types = set(map(type, components))
        same_type_components = [c for c in self._component_dict if type(c) in overwrite_types]
        self.disconnect(*same_type_components)

    def _modify_signal_map(self, c: SpectraComponent, cmd_dict:dict, list_op:str= "append") -> None:
        """ Add or remove callbacks from the signal map based on a dictionary of signals and callback data.
            Data items may be either a raw callable or a tuple with a callable and subsequent commands. """
        for (signal, data) in cmd_dict.items():
            callback_tuple = (c, *data) if isinstance(data, tuple) else (c, data)
            getattr(self._signal_map[signal], list_op)(callback_tuple)

    def send(self, command:str, *args) -> None:
        """ Call the methods listed under <command>, piping the output to other commands in each tuple. """
        for cmp, func, *pipe_to in self._signal_map[command]:
            try:
                # Call the method and recursively call output commands (if any) with the return value.
                val = func(*args)
                for cmd in pipe_to:
                    self.send(cmd, val)
            except RuntimeError:
                # If we got here, we tried to call a method on a deleted object.
                # Disconnect it from the engine if it's still there.
                if cmp in self._component_dict:
                    self.disconnect(cmp)
