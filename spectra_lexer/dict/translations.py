import json
from typing import Iterable, List, Mapping, Tuple

from spectra_lexer import fork, on, pipe
from spectra_lexer.utils import merge
from spectra_lexer.dict.manager import ResourceManager


class TranslationsManager(ResourceManager):

    R_TYPE = "translations"

    @fork("dict_load_translations", "new_translations")
    def load_translations(self, filenames:Iterable[str]=None) -> dict:
        """ Load and merge every translation dictionary given.
            If none are given, attempt to find dictionaries belonging to a Plover installation and load those. """
        if filenames is not None:
            dicts = [self.engine_call("file_load", f) for f in filenames]
        else:
            dicts = self._decode_plover_cfg_translations()
        return merge(dicts)

    def _decode_plover_cfg_translations(self) -> List[dict]:
        """ Attempt to find the local Plover user directory and, if found, decode all dictionary files
            in the correct priority order (reverse of normal, since earlier keys overwrite later ones). """
        try:
            cfg_dict = self._get_plover_file("plover.cfg")
            dict_section = cfg_dict['System: English Stenotype']['dictionaries']
            # The section we need is read as a string, but it must be decoded as a JSON array.
            dict_filenames = [e['path'] for e in reversed(json.loads(dict_section))]
            return [self._get_plover_file(f) for f in dict_filenames]
        except OSError:
            # Catch-all for file loading errors. Just assume the required files aren't there and move on.
            pass
        except KeyError:
            print("Could not find dictionaries in plover.cfg.")
        except json.decoder.JSONDecodeError:
            print("Problem decoding JSON in plover.cfg.")
        return []

    def _get_plover_file(self, filename:str) -> dict:
        """ Get a file from the Plover user directory. If it doesn't exist, make sure we get the exception. """
        return self.engine_call("file_load", "~plover/" + filename)

    @pipe("dict_save_translations", "file_save", unpack=True)
    def save_translations(self, filename:str, translations:Mapping) -> Tuple[str, Mapping]:
        """ Not strictly necessary; the file handler will work directly for this, but it preserves uniformity. """
        return filename, translations
