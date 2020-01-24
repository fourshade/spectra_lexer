""" Package for the steno components of Spectra. These handle operations related to steno rules and translations. """

from typing import Any, Dict, Tuple

from spectra_lexer.display import DisplayData, DisplayOptions
from spectra_lexer.engine import AnalyzerOptions, StenoEngine, SearchOptions
from spectra_lexer.resource import RTFCREDict, RTFCREExamplesDict
from spectra_lexer.search import SearchResults
from spectra_lexer.resource.config import ConfigDictionary


class EngineOptions(SearchOptions, AnalyzerOptions, DisplayOptions):
    """ Combined namespace dict for all steno engine options. """

    def __init__(self, **kwargs) -> None:
        """ Add keyword arguments as attributes. """
        self.__dict__.update(kwargs)


class StenoGUIOutput:
    """ Data class that contains an entire GUI update. All fields are optional. """

    search_input: str = None              # Product of an example search action.
    search_results: SearchResults = None  # Product of a search action.
    display_data: DisplayData = None      # Product of a query action.


class StenoApplication:
    """ Common layer for user operations (resource I/O, GUI actions, analysis...it all goes through here). """

    _index_filename = ""   # Holds filename for index; set on first load.
    _config_filename = ""  # Holds filename for config; set on first load.
    is_first_run = False   # Set to True if we fail to load the config file.

    def __init__(self, config:ConfigDictionary, engine:StenoEngine) -> None:
        self._config = config  # Keeps track of configuration options in a master dict.
        self._engine = engine  # Main steno analysis engine.

    def load_translations(self, *filenames:str) -> None:
        """ Load and merge translations from JSON files. """
        translations = RTFCREDict.from_json_files(*filenames)
        self.set_translations(translations)

    def set_translations(self, translations:RTFCREDict) -> None:
        """ Send a new translations dict to the engine. """
        self._engine.set_search_translations(translations)

    def load_examples(self, filename:str) -> None:
        """ Load an examples index from a JSON file. Ignore file I/O errors since it may be missing. """
        self._index_filename = filename
        try:
            index = RTFCREExamplesDict.from_json_file(filename)
            self.set_examples(index)
        except OSError:
            pass

    def set_examples(self, index:RTFCREExamplesDict) -> None:
        """ Send a new examples index dict to the search engine. """
        self._engine.set_search_examples(index)

    def load_config(self, filename:str) -> None:
        """ Load config settings from a CFG file.
            If the file is missing, set the 'first run' flag and start a new one. """
        self._config_filename = filename
        try:
            self._config.read_cfg(filename)
        except OSError:
            self.set_config({})
            self.is_first_run = True

    def set_config(self, options:Dict[str, Any]) -> None:
        """ Update the config dict with <options> and save them back to the original CFG file. """
        assert self._config_filename
        self._config.update(options)
        self._config.write_cfg(self._config_filename)

    def make_index(self, *args, **kwargs) -> None:
        """ Run the lexer on all <translations> with an input filter and look at the top-level rule names.
            Make an examples index containing a dict for each built-in rule with every translation that used it.
            Finish by setting them active and saving them to disk. """
        assert self._index_filename
        index = self._engine.make_index(*args, **kwargs)
        self.set_examples(index)
        index.json_dump(self._index_filename)

    def _with_config(self, options:dict) -> EngineOptions:
        """ Add config options first. The main <options> will override them. """
        d = self._config.to_dict()
        d.update(options)
        return EngineOptions(**d)

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
