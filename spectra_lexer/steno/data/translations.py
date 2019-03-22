import json
from typing import Dict, List, Optional, Sequence

from spectra_lexer import Component
from spectra_lexer.utils import ensure_list, merge


# Plover's app user dir and config filename. Dictionaries are located in the same directory.
_PLOVER_USER_DIR = "~plover/"
_PLOVER_CFG_FILENAME = "plover.cfg"
# By default, the sentinel value 'PLOVER' means 'try and find the files from Plover on start'.
_PLOVER_SENTINEL = "PLOVER"


class TranslationsManager(Component):
    """ Translation parser for the Spectra program. The structures are just string dicts
        that require no extra processing after conversion to/from JSON. """

    files = Resource("cmdline", "translations-files", [_PLOVER_SENTINEL], "JSON translation files to load on startup.")
    out = Resource("cmdline", "translations-out", "translations.json", "Output file name for steno translations.")

    @on("cmdline_opts_done", pipe_to="new_translations")
    @on("translations_load", pipe_to="new_translations")
    def load(self, filenames:Sequence[str]=()) -> Dict[str, str]:
        """ Load and merge translations from disk. """
        patterns = filenames or self.files
        if _PLOVER_SENTINEL in patterns:
            patterns = self._plover_files()
        if any(patterns):
            return merge(self.engine_call("file_load_all", *patterns))

    @on("translations_save", pipe_to="file_save")
    def save(self, d:Dict[str, str], filename:str="") -> tuple:
        """ Save a translations dict directly into JSON. If no save filename is given, use the default. """
        return (filename or self.out), d

    def _plover_files(self) -> List[str]:
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

    @on("show_translation")
    def show(self, *items) -> Optional[tuple]:
        """ Send a lexer query so we can show a translation. <items> are usually (stroke, word) or lists thereof. """
        if not all(isinstance(i, str) for i in items):
            # If there is more than one of any input, make a product query to select the best combination.
            return self.engine_call("lexer_query_product", *map(ensure_list, items))
        # By default, the items are assumed to be direct lexer input. """
        return self.engine_call("lexer_query", *items)
