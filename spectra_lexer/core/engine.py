from collections import defaultdict
from typing import Any, Dict, Hashable


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

    _cmd_dict: Dict[Hashable, list]  # Mappings for every command to a list of registered functions/dispatchers.

    def __init__(self, commands:list):
        """ Initialize the engine with (key, (func, dispatch)) command tuples. """
        d = self._cmd_dict = defaultdict(list)
        for (k, cmd) in commands:
            d[k].append(cmd)

    def call(self, cmd_key:Hashable, *args, is_top:bool=True, **kwargs) -> Any:
        """ Re-entrant method for engine calls. Checks exceptions with a custom handler. """
        try:
            value = None
            # Run all commands under this key and return the last value.
            for func, next_key, cmd_kwargs in self._cmd_dict[cmd_key]:
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
