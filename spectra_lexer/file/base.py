import configparser
import json
import os
from pathlib import Path
from typing import Dict, Iterable, List, NamedTuple

from spectra_lexer.engine import SpectraEngineComponent
from spectra_lexer.file.decoder import get_supported_file_formats, recursive_decode_all
from spectra_lexer.file.parser import StenoRuleDict
from spectra_lexer.rules import StenoRule

# Local directory containing the built-in JSON-based rules files.
_RULES_DIR: str = os.path.join(os.path.dirname(__file__), "..", "assets")
# Default directory in user space for Plover configuration/assets on Windows.
_PLOVER_USER_DIR: str = os.path.join("AppData", "Local", "plover", "plover")


def _dict_files_from_plover_cfg() -> Iterable[str]:
    """ Get an iterator containing all dictionaries from the local Plover installation.
        Return them in priority order (reverse of normal, since earlier keys overwrite later ones). """
    files = []
    ploverdir = os.path.join(str(Path.home()), _PLOVER_USER_DIR)
    cfg = configparser.ConfigParser()
    cfg_read = cfg.read(os.path.join(ploverdir, "plover.cfg"))
    if cfg_read:
        try:
            dict_section = cfg['System: English Stenotype']['dictionaries']
            for d in json.loads(dict_section):
                files.append(os.path.join(ploverdir, d['path']))
        except KeyError:
            print("Could not find dictionaries in plover.cfg.")
        except json.decoder.JSONDecodeError:
            print("Problem decoding JSON in plover.cfg.")
    return reversed(files)


class RawStenoDictionary(Dict[str, str]):
    """
    Class for creating an unformatted steno dictionary from a set of files.
    Each file contains a single JSON dict with the following key-value pairs:

    key   - A series of steno keys in RTFCRE format. Strokes are separated with the "/" delimiter.
    value - An English text translation.
    """

    def __init__(self, *filenames:str):
        """ Load every steno dict found in the given filenames. """
        super().__init__()
        for d in recursive_decode_all(filenames):
            self.update(d)


class RawRule(NamedTuple):
    """ Data structure for raw string fields read from each line in a JSON rules file. """
    keys: str              # RTFCRE formatted series of steno strokes.
    pattern: str           # English text pattern, consisting of raw letters as well as references to other rules.
    flag_str: str = ""     # Optional pipe-delimited series of flags.
    description: str = ""  # Optional description for when the rule is displayed in the GUI.
    example_str: str = ""  # Optional pipe-delimited series of example translations using this rule.


class RawRulesDictionary(Dict[str, RawRule]):
    """
    Class for creating an unformatted rules dictionary from a set of files.
    Each file contains a single JSON dict with the following key-value pairs:

    key   - Canonical name for the rule. Used as a reference in the <pattern> field of other rules.
    value - List of 2-5 string parameters, converted to a RawRule named tuple for field access.
    """

    def __init__(self, *filenames:str):
        """ Load every rules dict found in the given filenames, or the built-in ones if not specified. """
        src_dicts = recursive_decode_all(filenames or [_RULES_DIR])
        super().__init__({k: RawRule(*d[k]) for d in src_dicts for k in d})


def load_steno_dicts(filenames:Iterable[str]=()) -> RawStenoDictionary:
    """ Attempt to load and/or merge one or more steno dictionaries given by filename.
        If none were given, attempt to locate Plover's dictionaries and load those. """
    filenames = filenames or _dict_files_from_plover_cfg()
    return RawStenoDictionary(*filenames)


def load_rules_dicts(filenames:Iterable[str]=()) -> List[StenoRule]:
    """ Attempt to load one or more rules dictionaries given by filename.
        If none were given, attempt to locate Plover's dictionaries and load those.
        Parse them into finished form and send them in a list to the lexer. """
    filenames = filenames or [_RULES_DIR]
    d = RawRulesDictionary(*filenames)
    return list(StenoRuleDict(d).values())


class FileHandler(SpectraEngineComponent):
    """ Engine wrapper for file I/O operations. Directs engine commands to module-level functions. """

    def engine_commands(self) -> dict:
        """ Individual components must define the signals they respond to and the appropriate callbacks. """
        return {"file_load_steno_dicts": (load_steno_dicts,           "search_set_dict"),
                "file_load_rules_dicts": (load_rules_dicts,           "lexer_set_rules"),
                "file_get_dict_formats": (get_supported_file_formats, "gui_open_file_dialog")}
