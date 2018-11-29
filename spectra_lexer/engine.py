from collections import defaultdict
from typing import Callable, Dict, List, Optional

# TODO: implement threading and thread safety between GUI and processing components.

class SpectraEngineComponent:
    """ Mixin class for any component that sends and receives commands from the Spectra engine.
        Subclass must define commands it accepts (if any) by overriding engine_commands. """

    def engine_send(self, command:str, *args) -> Exception:
        """ Any command that gets called by an (unintentionally) unconnected component raises an error. """
        raise AttributeError("Signal sent by unconnected component.")

    def engine_commands(self) -> dict:
        """ Components provide a dict with the commands they accept here. By default, they accept nothing. """
        return {}

    def set_engine_callback(self, callback:Optional[Callable]=None) -> None:
        """ Override the engine_send method to start sending commands to the engine via <callback>.
            If <callback> is None, run the component without the engine by setting engine_send to do nothing. """
        if callback is None:
            self.engine_send = lambda *args: None
        else:
            self.engine_send = callback

    def remove_engine_callback(self) -> None:
        """ Remove the engine_send instance method so it throws an exception again. """
        del self.engine_send


class SpectraEngine:
    """
    Top-level class for operation of the Spectra program. Instantiated by the master GUI widget very
    shortly after initialization. Is expected to persist across multiple windows when used as a plugin.

    The program itself is conceptually divided into three parts that form a pipeline:
        Search/input - translations for the program to parse have to come from somewhere, and usually it's a JSON
        dictionary loaded from outside. The search component handles all search functionality and sends queries
        to the lexer at certain points when the old information is ready to be overwritten by new information.

        Lexer/processing - A translation consists of a series of strokes mapped to an English word, and it is the
        lexer's job to match pieces of each using a dictionary of rules it has loaded from storage. All rules handling
        is done by the lexer component, including parsing them from JSON files on disk and converting them back
        if need be. All results are handed off to the output component, which decides their fate.

        Display/output - The lexer provides its output (usually a rule constructed from user input) to this component
        which puts it in its final form for the GUI to display, including the text graph and the steno board layout
        diagram. This is strictly one-way - no information needs to pass back to the lexer or search from here.

    This class glues these three components together, handling communication between each one and the GUI as well as
    passing information from one stage of the pipeline to the next. Facilitating communication is *all* it should do;
    any actual software functionality should be implemented in one of the three component classes or the GUI.

    This object must handle calls from above as well as below; in particular, the search engine must be able to
    accept dictionaries from the main window, and the lexer must be able to accept queries from the Plover layer.
    """

    _component_dict: Dict[SpectraEngineComponent, dict]  # Dict mapping components to their command dicts, id hashed.
    _signal_map: Dict[str, List[tuple]]                  # Mapping of every command to a list of callback structures.

    def __init__(self, *components:SpectraEngineComponent):
        self._component_dict = {}
        self._signal_map = defaultdict(list)
        self.connect(*components)

    def connect(self, *components:SpectraEngineComponent, overwrite:bool=False) -> None:
        """ Connect all of the specified components to the engine, adding their commands to the signal table.
            If overwrite is True, disconnect any existing instances of the new components first. """
        if overwrite:
            self._disconnect_same_type_as(*components)
        for c in components:
            if c in self._component_dict:
                raise KeyError("Component is already connected.")
            cmd_dict = c.engine_commands()
            self._component_dict[c] = cmd_dict
            self._modify_signal_map(c, cmd_dict, list_op="append")
            c.set_engine_callback(self.send)

    def disconnect(self, *components:SpectraEngineComponent) -> None:
        """ Disconnect all of the specified components, removing all dict entries and callbacks. """
        for c in components:
            cmd_dict = self._component_dict.get(c)
            if c is None:
                raise KeyError("Component is not connected.")
            c.remove_engine_callback()
            self._modify_signal_map(c, cmd_dict, list_op="remove")
            del self._component_dict[c]

    def _disconnect_same_type_as(self, *components:SpectraEngineComponent) -> None:
        """ Disconnect all instances of the same type as the specified components. """
        overwrite_types = set(map(type, components))
        same_type_components = [c for c in self._component_dict if type(c) in overwrite_types]
        self.disconnect(*same_type_components)

    def _modify_signal_map(self, c:SpectraEngineComponent, cmd_dict:dict, list_op:str="append") -> None:
        """ Add or remove callbacks from the signal map based on a dictionary of signals and callback data.
            Data items may be either a raw callable or a tuple with a callable and subsequent commands. """
        for (signal, data) in cmd_dict.items():
            callback_tuple = (c, *data) if isinstance(data, tuple) else (c, data)
            getattr(self._signal_map[signal], list_op)(callback_tuple)

    def start(self) -> None:
        """ Send a start command to any components that handle it. Must be called after engine setup. """
        # TODO: Use this method to start a separate thread for the engine.
        self.send("engine_start")

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
