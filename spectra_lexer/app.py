import json
from typing import Any, Dict, List

from .config import ConfigDictionary, ConfigItem
from .io import ResourceIO
from .steno import ExamplesDict, StenoEngine, StenoGUIOutput, TranslationsDict


class StenoApplication:
    """ Common layer for user operations (resource I/O, GUI actions, batch analysis...it all goes through here). """

    def __init__(self, io:ResourceIO, engine:StenoEngine, config:ConfigDictionary) -> None:
        self._io = io              # Handles all resource loading, saving, and transcoding.
        self._engine = engine      # Runtime engine for steno operations such as parsing and graphics.
        self._config = config      # Keeps track of configuration options in a master dict.
        self._index_file = ""      # Holds filename for index; set on first load.
        self._config_file = ""     # Holds filename for config; set on first load.
        self.is_first_run = False  # Set to True if we fail to load the config file.

    def load_translations(self, *filenames:str) -> None:
        """ Load and merge translations from JSON files. """
        translations = {}
        for filename in filenames:
            with self._io.open(filename, 'r') as fp:
                d = json.load(fp)
            translations.update(d)
        self.set_translations(translations)

    def set_translations(self, translations:TranslationsDict) -> None:
        """ Send a new translations dict to the engine. """
        self._engine.set_translations(translations)

    def load_index(self, filename:str) -> None:
        """ Load an examples index from a JSON file. Ignore missing files. """
        self._index_file = filename
        try:
            with self._io.open(filename, 'r') as fp:
                index = json.load(fp)
            self.set_index(index)
        except OSError:
            pass

    def make_index(self, *args, **kwargs) -> None:
        """ Make a index for each built-in rule containing a dict of every translation that used it.
            Finish by setting them active and saving them to disk. """
        index = self._engine.make_index(*args, **kwargs)
        self.set_index(index)
        self.save_index(index)

    def set_index(self, index:ExamplesDict) -> None:
        """ Send a new examples index dict to the engine. """
        self._engine.set_index(index)

    def save_index(self, index:ExamplesDict) -> None:
        """ Save an examples index structure to a JSON file.
            Dict key sorting helps search algorithms run faster.
            An explicit flag is required to preserve Unicode symbols. """
        assert self._index_file
        data = json.dumps(index, sort_keys=True, ensure_ascii=False)
        with self._io.open(self._index_file, 'w') as fp:
            fp.write(data)

    def load_config(self, filename:str) -> None:
        """ Load config settings from a CFG file.
            If the file is missing, set a 'first run' flag and start a new one. """
        self._config_file = filename
        try:
            with self._io.open(filename, 'r') as fp:
                self._config.read_cfg(fp)
        except OSError:
            self.is_first_run = True
            self.save_config()

    def set_config(self, options:Dict[str, Any]) -> None:
        """ Update the config dict with <options> and save them to disk. """
        self._config.update(options)
        self.save_config()

    def save_config(self) -> None:
        """ Save config settings into a CFG file. """
        assert self._config_file
        with self._io.open(self._config_file, 'w') as fp:
            self._config.write_cfg(fp)

    def get_config_info(self) -> List[ConfigItem]:
        """ Return all active config info with formatting instructions. """
        return self._config.info()

    def process_action(self, *args, **options) -> StenoGUIOutput:
        """ Perform an action and return the changes.
            Config options are added to the view state first. The main options may override them. """
        options = {**self._config.to_dict(), **options}
        return self._engine.process_action(*args, **options)
