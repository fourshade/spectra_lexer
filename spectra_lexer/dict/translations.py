import json
from typing import List

from spectra_lexer.dict.manager import ResourceManager

# Plover's app user dir and config filename. Dictionaries are located on the same level.
_PLOVER_USER_DIR: str = "~plover/"
_PLOVER_CFG_FILENAME: str = "plover.cfg"


class TranslationsManager(ResourceManager):

    ROLE = "dict_translations"
    CMD_SUFFIX = "translations"
    OPT_KEY = "search"

    def load_default(self) -> List[dict]:
        """ Attempt to find the local Plover user directory and, if found, decode all dictionary files
            in the correct priority order (reverse of normal, since earlier keys overwrite later ones). """
        try:
            cfg_dict = self.engine_call("file_load", _PLOVER_USER_DIR + _PLOVER_CFG_FILENAME)[0]
            dict_section = cfg_dict['System: English Stenotype']['dictionaries']
            # The section we need is read as a string, but it must be decoded as a JSON array.
            dict_filenames = [_PLOVER_USER_DIR + e['path'] for e in reversed(json.loads(dict_section))]
            return self.engine_call("file_load", *dict_filenames)
        except OSError:
            # Catch-all for file loading errors. Just assume the required files aren't there and move on.
            pass
        except KeyError:
            print("Could not find dictionaries in plover.cfg.")
        except json.decoder.JSONDecodeError:
            print("Problem decoding JSON in plover.cfg.")
        return []
