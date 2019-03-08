import json
from typing import List, Sequence

from spectra_lexer import Component
from spectra_lexer.utils import merge

# Plover's app user dir and config filename. Dictionaries are located in the same directory.
_PLOVER_USER_DIR = "~plover/"
_PLOVER_CFG_FILENAME = "plover.cfg"


class TranslationsManager(Component):
    """ Translation parser for the Spectra program. The structures are just string dicts
        that require no extra processing after conversion to/from JSON. """

    ROLE = "translations"
    files = Option("cmdline", "translations-files", [], "Glob patterns for JSON-based translations files to load.")
    out = Option("cmdline", "translations-out", "translations.json", "Output file name for translations.")

    @pipe("start", "translations_load")
    def start(self, **opts) -> tuple:
        """ Load translations at startup. By default, an empty list and means 'try and find the files from Plover'.
            This can be suppressed by setting one or more of the string values to 'IGNORE'. """
        # If the file menu is used, add a basic file dialog command.
        self.engine_call("file_add_dialog", "translations", menu_pos=1)
        if "IGNORE" not in self.files:
            return ()

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
        """ Load and merge translations from disk. """
        return merge(self.engine_call("file_load_all", *(filenames or self.files or self._default_files())))

    @pipe("translations_save", "file_save")
    def save(self, d:dict, filename:str="") -> tuple:
        """ Save a translations dict directly into JSON. If no save filename is given, use the default file. """
        return (filename or self.out), d
