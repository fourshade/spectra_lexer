from functools import partial
import json
import os
from typing import Dict, Iterable, List

from .base import RS
from .keys import KeyLayout
from .parser import RuleParser
from .rules import StenoRule
from .xml import XMLElement
from spectra_lexer.core import CmdlineOption, CORE

# Plover's app user dir and config filename. Dictionaries are located in the same directory.
_PLOVER_USER_DIR = "~plover/"
_PLOVER_CFG_FILENAME = _PLOVER_USER_DIR + "plover.cfg"


class ResourceManager(CORE, RS):
    """ Component to load all resources necessary for a steno system. The structures are mostly JSON dicts.
        Assets including a key layout, rules, and (optional) board graphics comprise the system.
        Other files from user space include a translations dictionary and examples index. """

    system_path: str = CmdlineOption("system-dir", default=":/assets/",
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

    _rule_parser: RuleParser = None

    def Load(self) -> None:
        """ Load every available asset into its global resource attribute before startup.
            Search for translations dictionaries from Plover if no changes were made to the command line option. """
        self.COREStatus("Loading...")
        self.RSSystemLoad(self.system_path)
        self.RSTranslationsLoad(*(self.translation_files or self._plover_files()))
        self.RSIndexLoad(self.index_file)
        self.RSConfigLoad(self.config_file)
        self.COREStatus("Loading complete.")

    def RSSystemLoad(self, base_dir:str) -> dict:
        with_path = partial(os.path.join, base_dir)
        d = {"layout":      self._load_layout(with_path("layout.json")),           # Steno key constants.
             "rules":       self._load_rules(with_path("*.cson")),                 # CSON rules glob pattern.
             "board_defs":  self._load_board_defs(with_path("board_defs.json")),   # Board shape definitions.
             "board_elems": self._load_board_elems(with_path("board_elems.xml"))}  # XML steno board elements.
        self.RSSystemReady(**d)
        return d

    def _load_layout(self, layout_path:str) -> KeyLayout:
        layout_data = self._load_one(layout_path)
        layout_dict = json_decode(layout_data)
        return KeyLayout(layout_dict)

    def _load_rules(self, rules_path:str) -> Dict[str, StenoRule]:
        rules_data_list = self._load(rules_path)
        raw_dict = cson_decode(*rules_data_list)
        self._rule_parser = RuleParser(raw_dict)
        return self._rule_parser

    def _load_board_defs(self, defs_path:str) -> dict:
        defs_data = self._load_one(defs_path)
        return json_decode(defs_data)

    def _load_board_elems(self, elems_path:str) -> XMLElement:
        elems_data = self._load_one(elems_path)
        return XMLElement.decode(elems_data)

    def RSTranslationsLoad(self, *patterns:str, **kwargs) -> Dict[str, str]:
        translations = json_decode(*self._load(*patterns), **kwargs)
        self.RSTranslationsReady(translations)
        return translations

    def RSIndexLoad(self, filename:str, **kwargs) -> Dict[str, dict]:
        index = json_decode(self._load_one(filename), **kwargs)
        self.RSIndexReady(index)
        return index

    def RSConfigLoad(self, filename:str, **kwargs) -> Dict[str, dict]:
        cfg = cfg_decode(self._load_one(filename), **kwargs)
        self.RSConfigReady(cfg)
        return cfg

    def _load(self, *patterns) -> List[bytes]:
        return self.COREFileLoad(*patterns)

    def _load_one(self, *patterns) -> bytes:
        data_list = self.COREFileLoad(*patterns)
        if not data_list:
            return b""
        return data_list[0]

    def RSRulesSave(self, rules:Iterable[StenoRule], filename:str="", **kwargs) -> None:
        raw_dict = self._rule_parser.compile_to_raw(rules)
        self._save(json_encode(raw_dict, **kwargs), filename or self.rules_out)

    def RSTranslationsSave(self, translations:Dict[str, str], filename:str="", **kwargs) -> None:
        self._save(json_encode(translations, **kwargs), filename or self.translations_out)

    def RSIndexSave(self, index:Dict[str, dict], filename:str="", **kwargs) -> None:
        self._save(json_encode(index, **kwargs), filename or self.index_file)

    def RSConfigSave(self, cfg:Dict[str, dict], filename:str="", **kwargs) -> None:
        self._save(cfg_encode(cfg, **kwargs), filename or self.config_file)

    def _save(self, data:bytes, filename:str) -> None:
        self.COREFileSave(data, filename)

    def _plover_files(self) -> List[str]:
        """ Attempt to find the local Plover user directory and, if found, decode all dictionary files
            in the correct priority order (reverse of normal, since earlier keys overwrite later ones). """
        try:
            cfg = cfg_decode(self._load_one(_PLOVER_CFG_FILENAME))
            if cfg:
                section = cfg['System: English Stenotype']['dictionaries']
                # The section we need is read as a string, but it must be decoded as a JSON array.
                return [_PLOVER_USER_DIR + e['path'] for e in reversed(json.loads(section))]
        except OSError:
            # Catch-all for file loading errors. Just assume the required files aren't there and move on.
            pass
        except KeyError:
            self.COREStatus("Could not find dictionaries in plover.cfg.")
        except ValueError:
            self.COREStatus("Problem decoding JSON in plover.cfg.")
        return []


def json_decode(*all_data:bytes, **kwargs) -> dict:
    """ Decode each byte string to a dict and merge them in order.
        JSON standard library functions are among the fastest ways to load structured data in Python. """
    d = {}
    for data in all_data:
        d.update(json.loads(data or b"{}", **kwargs))
    return d


def json_encode(d:dict, *, encoding:str='utf-8', **kwargs) -> bytes:
    """ Key sorting helps some parsing and search algorithms run faster.
        An explicit flag is required to preserve Unicode symbols. """
    kwargs = {"sort_keys": True, "ensure_ascii": False, **kwargs}
    return json.dumps(d, **kwargs).encode(encoding)


def cson_decode(*all_data:bytes, comment_prefixes=frozenset(b"#/"), **kwargs) -> dict:
    """ Decode each JSON byte string with full-line standalone comments. """
    d = {}
    for data in all_data:
        # JSON doesn't care about leading or trailing whitespace, so strip every line.
        stripped_line_iter = map(bytes.strip, data.splitlines())
        # Empty lines and lines starting with a comment tag after stripping are removed before parsing.
        data_lines = [line for line in stripped_line_iter if line and line[0] not in comment_prefixes]
        d.update(json.loads(b"\n".join(data_lines) or b"{}", **kwargs))
    return d


def cfg_decode(data:bytes, encoding:str='utf-8') -> dict:
    """ Decode CFG file contents into a nested dict.
        Parse lines of sectioned configuration data. Each section in a configuration file contains a header,
        indicated by a name in square brackets (`[]`), plus key/value options, indicated by `name = value`.
        Configuration files may include comments, prefixed by `#' or `;' in an otherwise empty line. """
    cfg = {}
    line_iter = data.decode(encoding).splitlines()
    cursect = None
    for line in line_iter:
        # strip full line comments
        line = line.strip()
        if line and line[0] not in '#;':
            # Parse as a section header: [ + header + ]
            if line[0] == "[" and line[-1] == "]":
                sectname = line[1:-1]
                cursect = cfg.setdefault(sectname, {})
            elif cursect is None:
                raise ValueError('No initial header in file.')
            # Parse as an option line: name + spaces/tabs + `=` delimiter + spaces/tabs + value
            elif "=" not in line:
                raise ValueError(f'Missing `=` for option in line: {line}.')
            else:
                optname, optval = line.split("=", 1)
                cursect[optname.rstrip()] = optval.lstrip()
    return cfg


def cfg_encode(cfg:dict, *, encoding:str='utf-8') -> bytes:
    """ Encode this dict into a config/INI formatted representation of the configuration state."""
    s_list = []
    for section in cfg:
        s_list += "\n[", section, "]\n"
        for key, value in cfg[section].items():
            if '\n' in key or '\n' in value:
                raise ValueError(f'Newline in option {key}: {value}')
            s_list += key, " = ", value, "\n"
    return "".join(s_list)[1:].encode(encoding)
