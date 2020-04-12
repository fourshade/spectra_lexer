""" Package for the steno components of Spectra. These handle operations related to steno rules and translations. """

from typing import Any, Dict, Tuple

from spectra_lexer.display import DisplayData
from spectra_lexer.engine import EngineOptions, StenoEngine
from spectra_lexer.resource.config import Configuration
from spectra_lexer.resource.translations import RTFCREDict
from spectra_lexer.search import SearchResults


class StenoGUIOutput:
    """ Data class that contains an entire GUI update. All fields are optional. """

    search_input: str = None              # Product of an example search action.
    search_results: SearchResults = None  # Product of a search action.
    display_data: DisplayData = None      # Product of a query action.


class StenoApplication:
    """ Common layer for user operations (resource I/O, GUI actions, analysis...it all goes through here). """

    def __init__(self, config:Configuration, engine:StenoEngine) -> None:
        self._config = config      # Keeps track of configuration options in a master dict.
        self._engine = engine      # Main steno analysis engine.
        self._index_filename = ""  # Holds filename for index; set on first load.

    def load_translations(self, *filenames:str) -> None:
        self._engine.load_translations(*filenames)

    def set_translations(self, translations:RTFCREDict) -> None:
        """ Send a new translations dict to the engine. """
        self._engine.set_translations(translations)

    def load_examples(self, filename:str) -> None:
        """ Load an examples index from a JSON file. Ignore file I/O errors since it may be missing. """
        self._index_filename = filename
        try:
            self._engine.load_examples(filename)
        except OSError:
            pass

    def load_config(self) -> bool:
        """ Load config settings from a CFG file. If the file is missing, start a new one and return True. """
        try:
            self._config.read()
            return False
        except OSError:
            self._config.write()
            return True

    def set_config(self, options:Dict[str, Any]) -> None:
        """ Update the config dict with <options> and save them back to the original CFG file. """
        self._config.update(options)
        self._config.write()

    def make_index(self, *args, **kwargs) -> None:
        """ Run the lexer on all <translations> with an input filter and look at the top-level rule names.
            Make an examples index containing a dict for each built-in rule with every translation that used it.
            Finish by setting them active and saving them to disk. """
        assert self._index_filename
        self._engine.compile_examples(*args, **kwargs)
        self._engine.save_examples(self._index_filename)

    def _with_config(self, options:dict) -> EngineOptions:
        """ Add config options first. The main <options> will override them. """
        opts = EngineOptions()
        vars(opts).update(self._config.to_dict())
        vars(opts).update(options)
        return opts

    def gui_search(self, pattern:str, pages=1, **options) -> StenoGUIOutput:
        """ Do a new search and return results unless the input is blank. """
        output = StenoGUIOutput()
        engine_options = self._with_config(options)
        if pattern.strip():
            output.search_results = self._engine.search(pattern, pages, options=engine_options)
        return output

    def gui_query(self, translation:Tuple[str, str], *others:Tuple[str, str], **options) -> StenoGUIOutput:
        """ Execute and display a graph of a lexer query from search results or user strokes. """
        output = StenoGUIOutput()
        engine_options = self._with_config(options)
        if others:
            analysis = self._engine.analyze_best(translation, *others, options=engine_options)
        else:
            analysis = self._engine.analyze(*translation, options=engine_options)
        output.display_data = self._engine.display(analysis, options=engine_options)
        return output

    def gui_search_examples(self, link_ref:str, **options) -> StenoGUIOutput:
        """ When a link is clicked, search for examples of the named rule and select one. """
        output = StenoGUIOutput()
        engine_options = self._with_config(options)
        keys, letters, pattern = self._engine.random_example(link_ref, engine_options)
        if keys and letters:
            output = self.gui_query((keys, letters), **options)
            output.search_input = pattern
            output.search_results = self._engine.search(pattern, 1, engine_options)
        return output

    def console_vars(self) -> dict:
        """ Return variables suitable for direct use in an interactive Python console. """
        return {k: getattr(self, k) for k in dir(self) if not k.startswith('_')}
