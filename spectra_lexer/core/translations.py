import json
from typing import List, Sequence

from spectra_lexer import Component, pipe
from spectra_lexer.utils import merge

# Plover's app user dir and config filename. Dictionaries are located in the same directory.
_PLOVER_USER_DIR = "~plover/"
_PLOVER_CFG_FILENAME = "plover.cfg"
# Default output file name for user translations.
_TRANSLATIONS_OUTPUT_FILE = "translations.json"


class TranslationsManager(Component):
    """ Translation parser for the Spectra program. The structures are just string dicts
        that require no extra processing after conversion to/from JSON. """

    ROLE = "translations"

    @pipe("start", "translations_load")
    def start(self, translations:str=None, **opts) -> Sequence[str]:
        """ If there is a command line option for this component, even if empty, attempt to load translations.
            If the option is present but empty (or otherwise evaluates False), use the defaults instead. """
        if translations is not None:
            return [translations] if translations else ()

    def _default_files(self) -> List[str]:
        """ Attempt to find the local Plover user directory and, if found, decode all dictionary files
            in the correct priority order (reverse of normal, since earlier keys overwrite later ones). """
        try:
            cfg_dict = self.engine_call("file_load", _PLOVER_USER_DIR + _PLOVER_CFG_FILENAME)
            dict_section = cfg_dict['System: English Stenotype']['dictionaries']
            # The section we need is read as a string, but it must be decoded as a JSON array.
            return [_PLOVER_USER_DIR + e['path'] for e in reversed(json.loads(dict_section))]
        except OSError:
            # Catch-all for file loading errors. Just assume the required files aren't there and move on.
            pass
        except KeyError:
            print("Could not find dictionaries in plover.cfg.")
        except json.decoder.JSONDecodeError:
            print("Problem decoding JSON in plover.cfg.")
        return []

    @pipe("translations_load", "new_translations")
    def load(self, filenames:Sequence[str]=()) -> dict:
        """ Load and merge translations from disk. If no filenames are given by the command,
            try to find and load the ones from Plover by defaults. """
        return merge(self.engine_call("file_load_all", *(filenames or self._default_files())))

    @pipe("translations_save", "file_save")
    def save(self, filename:str, d:dict) -> tuple:
        """ Save a translations dict directly into JSON. If no save filename is given, use the default file. """
        return (filename or _TRANSLATIONS_OUTPUT_FILE), d
