""" Module for advanced path operations. Contains instructions for loading initial resources. """

import json
import os
from typing import List, Optional

from spectra_lexer.file.codecs import decode_resource
from spectra_lexer.file.resource import Asset, File, glob_assets

# Resource path containing the built-in JSON-based rules files
_RULES_ASSET_PATH: str = "*.cson"
# File path to the user's config file. Must be in user space (light permissions).
_CONFIG_FILE_PATH: str = "config.cfg"


def config_from_user_data() -> Optional[File]:
    """ Return the path the user config file (if present). """
    return File(_CONFIG_FILE_PATH) if os.path.isfile(_CONFIG_FILE_PATH) else None


def rules_from_assets_dir() -> List[Asset]:
    """ Return a list containing all built-in rules files packaged with the program. """
    return glob_assets(_RULES_ASSET_PATH)


def dict_files_from_plover_cfg() -> List[File]:
    """ Attempt to find the local Plover installation and, if found, return a list containing all dictionary
        files in the correct priority order (reverse of normal, since earlier keys overwrite later ones). """
    for path in _user_data_paths('plover'):
        cfg_path = os.path.join(path, "plover.cfg")
        if os.path.isfile(cfg_path):
            try:
                cfg_dict = decode_resource(File(cfg_path))
                dict_section = cfg_dict['System: English Stenotype']['dictionaries']
                dict_file_entries = reversed(json.loads(dict_section))
                return [File(os.path.join(path, d['path'])) for d in dict_file_entries]
            except KeyError:
                print("Could not find dictionaries in plover.cfg.")
            except json.decoder.JSONDecodeError:
                print("Problem decoding JSON in plover.cfg.")
    return []


def _user_data_paths(appname:str) -> List[str]:
    """ Directories to search for an application's configuration/assets in user space. """
    paths = [os.path.join(os.path.expanduser('~'), "AppData", "Local", appname),    # Windows
             os.path.join(os.path.expanduser('~'), "AppData", "Roaming", appname),  # Windows
             os.path.expanduser('~/Library/Application Support/'),                  # Mac
             os.getenv('XDG_DATA_HOME', os.path.expanduser("~/.local/share"))]      # Linux
    return [os.path.join(path, appname) for path in paths if path is not None]
