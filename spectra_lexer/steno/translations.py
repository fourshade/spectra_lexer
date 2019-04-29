from typing import Dict, List, Union

from spectra_lexer.core import Component
from spectra_lexer.file import CFG, JSON
from spectra_lexer.utils import ensure_iterable, merge

# Plover's app user dir and config filename. Dictionaries are located in the same directory.
_PLOVER_USER_DIR = "~plover/"
_PLOVER_CFG_FILENAME = "plover.cfg"
# By default, the sentinel value 'PLOVER' means 'try and find the files from Plover on start'.
_PLOVER_SENTINEL = "PLOVER"


class TranslationsManager(Component):
    """ Translation parser for the Spectra program. The structures are just string dicts
        that require no extra processing after conversion to/from JSON. """

    files = resource("cmdline:translations-files", [_PLOVER_SENTINEL], desc="JSON translation files to load on startup.")
    out = resource("cmdline:translations-out", "translations.json", desc="Output file name for steno translations.")

    @on("init:translations")
    def start(self, *dummy) -> Dict[str, str]:
        return self.load()

    @on("translations_load")
    @pipe_to("res:translations")
    def load(self, filenames:Union[str, List[str]]="") -> Dict[str, str]:
        """ Load and merge translations from disk. """
        patterns = ensure_iterable(filenames or self.files)
        if _PLOVER_SENTINEL in patterns:
            patterns = _plover_files()
        if any(patterns):
            return merge(JSON.load_all(*patterns))

    @on("translations_save")
    def save(self, d:Dict[str, str], filename:str="") -> None:
        """ Save a translations dict directly into JSON. If no save filename is given, use the default. """
        JSON.save(filename or self.out, d)


def _plover_files() -> List[str]:
    """ Attempt to find the local Plover user directory and, if found, decode all dictionary files
        in the correct priority order (reverse of normal, since earlier keys overwrite later ones). """
    try:
        cfg_dict = CFG.load(_PLOVER_USER_DIR + _PLOVER_CFG_FILENAME)
        dict_section = cfg_dict['System: English Stenotype']['dictionaries']
        # The section we need is read as a string, but it must be decoded as a JSON array.
        return [_PLOVER_USER_DIR + e['path'] for e in reversed(JSON.decode(dict_section))]
    except OSError:
        # Catch-all for file loading errors. Just assume the required files aren't there and move on.
        pass
    except KeyError:
        print("Could not find dictionaries in plover.cfg.")
    except ValueError:
        print("Problem decoding JSON in plover.cfg.")
    return []
