from typing import ClassVar, Iterable

from spectra_lexer.display.cascaded_text import CascadedTextDisplay
from spectra_lexer.engine import SpectraEngine, SpectraEngineComponent
from spectra_lexer.file import FileHandler
from spectra_lexer.lexer import StenoLexer
from spectra_lexer.search import SearchEngine

# Default non-GUI engine components for basic operation of the program.
BASE_COMPONENTS = [FileHandler, StenoLexer, SearchEngine, CascadedTextDisplay]


class SpectraApplication:
    """
    Top-level class for operation of the Spectra program. Instantiated by the master GUI widget very
    shortly after initialization. Is expected to persist across multiple windows when used as a plugin.
    """

    # Instance attributes are lost when the container dialog is closed and re-opened.
    # The engine and its parts are relatively expensive to create, so save it on the class to retain its state.
    _engine: ClassVar[SpectraEngine] = None

    def __init__(self, *gui_components:Iterable[SpectraEngineComponent], files:Iterable[str]=None, **kwargs) -> None:
        # Create the engine only once, the first time the window is opened, and store it on the class.
        first_load = self._engine is None
        if first_load:
            SpectraApplication._engine = SpectraEngine(*[cmp() for cmp in BASE_COMPONENTS])
        # Connect new GUI objects (includes the Plover plugin layer) to the existing engine, overwriting the old ones.
        self._engine.connect(*gui_components, overwrite=True)
        # Only start the engine once everything is connected for the first time.
        if first_load:
            self._engine.start()
        # If <files> was given as a parameter, try to load the steno dictionary files inside it on start-up.
        # If the parameter was given but empty, make an attempt to locate Plover's dictionaries and load those. """
        if files is not None:
            self._engine.send("file_load_steno_dicts", files)
            src_string = "command line" if files else "Plover config"
            self._engine.send("gui_show_status_message", "Loaded dictionaries from {}.".format(src_string))
        # Send command to set up anything else that needs it for a new GUI.
        self._engine.send("new_window")
