import json
import os
from typing import List

from .base import BoardElementTree, ConfigDictionary, RS
from .index import StenoIndex
from .keys import KeyLayout
from .rules import RulesDictionary
from .translations import TranslationsDictionary
from spectra_lexer.system import CmdlineOption
from spectra_lexer.types.codec import CFGDict

# Plover's app user dir and config filename. Dictionaries are located in the same directory.
_PLOVER_USER_DIR = "~plover/"
_PLOVER_CFG_FILENAME = _PLOVER_USER_DIR + "plover.cfg"


class ResourceManager(RS):
    """ Component to load all resources necessary for a steno system. The structures are mostly JSON dicts.
        Assets including a key layout, rules, and (optional) board graphics comprise the system.
        Other files from user space include a translations dictionary and examples index. """

    system_path: str = CmdlineOption("system-dir", default=":/assets/default/",
                                     desc="Directory with system resources")
    translation_files: List[str] = CmdlineOption("translations-files", default=[],
                                                 desc="JSON translation files to load on start.")
    index_file: str = CmdlineOption("index-file", default="~/index.json",
                                    desc="JSON index file to load on start and/or write to.")
    config_file: str = CmdlineOption("config-file", default="~/config.cfg",
                                     desc="CFG file with config settings to load at start and/or write to.")
    translations_out: str = CmdlineOption("translations-out", default="./translations.json",
                                          desc="JSON translation file to save.")
    rules_out: str = CmdlineOption("rules-out", default="./rules.json",
                                   desc="Output file name for lexer-generated rules.")

    DIR_INFO = (("layout.json", KeyLayout,        "LAYOUT"),  # File name for the steno key constants.
                ("*.cson",      RulesDictionary,  "RULES"),   # Glob pattern for JSON-based rules files.
                ("board.xml",   BoardElementTree, "BOARD"))   # File name for the XML steno board graphics.

    def Load(self) -> None:
        """ Load every available asset into its global resource attribute before startup.
            Search for translations dictionaries from Plover if no changes were made to the command line option. """
        self.SYSStatus("Loading...")
        self.RSSystemLoad(self.system_path)
        self.RSTranslationsLoad(*(self.translation_files or self._plover_files()))
        self.RSIndexLoad(self.index_file)
        self.RSConfigLoad(self.config_file)
        self.SYSStatus("Loading complete.")

    def RSSystemLoad(self, base_dir:str) -> dict:
        d = {}
        for filename, codec_cls, attr in self.DIR_INFO:
            pattern = os.path.join(base_dir, filename)
            rs = d[attr] = self.SYSFileLoad(codec_cls, pattern)
            setattr(self, attr, rs)
        return d

    def RSTranslationsLoad(self, *patterns:str, **kwargs) -> TranslationsDictionary:
        translations = self.TRANSLATIONS = self.SYSFileLoad(TranslationsDictionary, *patterns, **kwargs)
        return translations

    def RSIndexLoad(self, *patterns:str, **kwargs) -> StenoIndex:
        index = self.INDEX = self.SYSFileLoad(StenoIndex, *patterns, **kwargs)
        return index

    def RSConfigLoad(self, *patterns:str, **kwargs) -> ConfigDictionary:
        cfg = self.CONFIG = self.SYSFileLoad(ConfigDictionary, *patterns, **kwargs)
        return cfg

    def RSRulesSave(self, rules:RulesDictionary, filename:str="", **kwargs) -> None:
        self.SYSFileSave(rules, filename or self.rules_out, **kwargs)

    def RSTranslationsSave(self, d:TranslationsDictionary, filename:str="", **kwargs) -> None:
        self.SYSFileSave(d, filename or self.translations_out, **kwargs)

    def RSIndexSave(self, index:StenoIndex, filename:str="", **kwargs) -> None:
        self.SYSFileSave(index, filename or self.index_file, **kwargs)

    def RSConfigSave(self, cfg:ConfigDictionary, filename:str="", **kwargs) -> None:
        self.SYSFileSave(cfg, filename or self.config_file, **kwargs)

    def _plover_files(self) -> List[str]:
        """ Attempt to find the local Plover user directory and, if found, decode all dictionary files
            in the correct priority order (reverse of normal, since earlier keys overwrite later ones). """
        try:
            cfg = self.SYSFileLoad(CFGDict, _PLOVER_CFG_FILENAME)
            if cfg:
                section = cfg['System: English Stenotype']['dictionaries']
                # The section we need is read as a string, but it must be decoded as a JSON array.
                return [_PLOVER_USER_DIR + e['path'] for e in reversed(json.loads(section))]
        except OSError:
            # Catch-all for file loading errors. Just assume the required files aren't there and move on.
            pass
        except KeyError:
            self.SYSStatus("Could not find dictionaries in plover.cfg.")
        except ValueError:
            self.SYSStatus("Problem decoding JSON in plover.cfg.")
        return []
