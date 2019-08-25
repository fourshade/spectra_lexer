from collections import namedtuple
from functools import partial
import os
from typing import Dict, Iterable, TextIO

from .codec import cson_decode, cfg_decode, cfg_encode, json_decode, json_encode
from .io import PathIO
from .parser import RuleParser
from spectra_lexer.steno import KeyLayout, StenoRule

# Contains all static resources necessary for a steno system. The structures are mostly JSON dicts.
# Assets including a key layout, rules, and (optional) board graphics comprise the system.
StenoResources = namedtuple("StenoResources", "layout rules board_defs board_xml")


class ResourceLoader:
    """ Performs all necessary filesystem and asset I/O.
        Files from user space include a translations dictionary, an examples index, and a config file. """

    index_file: str = ""   # Holds filename for index; set on first load.
    config_file: str = ""  # Holds filename for config; set on first load.

    _rule_parser: RuleParser   # Parses rules from JSON and keeps track of the references for inverse parsing.

    def __init__(self, root_package:str) -> None:
        io = PathIO(root_package, root_package)
        self._read = io.read
        self._read_all = io.read_all
        self._write = io.write
        self._open = io.open
        self._rule_parser = RuleParser()

    def open_log_file(self, filename:str) -> TextIO:
        """ Open a file for logging (text mode, append to current contents) and return the stream. """
        stream = self._open(filename, 'a')
        return stream

    def load_resources(self, base_dir:str) -> StenoResources:
        """ Given a base directory, load each steno resource component by a standard name or pattern. """
        with_path = partial(os.path.join, base_dir)
        layout = self._load_layout(with_path("layout.json"))              # Steno key constants.
        rules = self._load_rules(with_path("*.cson"))                     # CSON rules glob pattern.
        board_defs = self._load_board_defs(with_path("board_defs.json"))  # Board shape definitions.
        board_xml = self._load_board_xml(with_path("board_elems.xml"))    # XML steno board elements.
        return StenoResources(layout, rules, board_defs, board_xml)

    def _load_layout(self, layout_path:str) -> KeyLayout:
        layout_data = self._read(layout_path)
        layout_dict = json_decode(layout_data)
        return KeyLayout(layout_dict)

    def _load_rules(self, rules_path:str) -> Dict[str, StenoRule]:
        rules_data_iter = self._read_all(rules_path)
        return self._rule_parser.parse(*map(cson_decode, rules_data_iter))

    def _load_board_defs(self, defs_path:str) -> dict:
        defs_data = self._read(defs_path)
        return json_decode(defs_data)

    def _load_board_xml(self, xml_path:str) -> bytes:
        return self._read(xml_path)

    def save_rules(self, rules:Iterable[StenoRule], filename:str) -> None:
        """ Parse a rules dictionary back into raw form and save it to JSON. """
        raw_dict = self._rule_parser.compile_to_raw(rules)
        self._write(json_encode(raw_dict), filename)

    def load_translations(self, *patterns:str) -> Dict[str, str]:
        """ Load and merge translations from disk. """
        translations = {}
        for data in self._read_all(*patterns):
            d = json_decode(data)
            translations.update(d)
        return translations

    def save_translations(self, translations:Dict[str, str], filename:str) -> None:
        """ Save a translations dict directly into JSON. """
        self._write(json_encode(translations), filename)

    def load_index(self, filename:str) -> Dict[str, dict]:
        """ Load an index from disk. """
        self.index_file = filename
        index_data = self._read(filename)
        index = json_decode(index_data)
        _check_compound_dict(index)
        return index

    def save_index(self, index:Dict[str, dict], filename:str="") -> None:
        """ Save an index structure directly into JSON. If no save filename is given, use the default. """
        _check_compound_dict(index)
        self._write(json_encode(index), filename or self.index_file)

    def load_config(self, filename:str) -> Dict[str, dict]:
        """ Load config settings from disk. """
        self.config_file = filename
        config_data = self._read(filename)
        cfg = cfg_decode(config_data)
        _check_compound_dict(cfg)
        return cfg

    def save_config(self, cfg:Dict[str, dict], filename:str="") -> None:
        """ Save a config dict into .cfg format. """
        _check_compound_dict(cfg)
        self._write(cfg_encode(cfg), filename or self.config_file)


def _check_compound_dict(d:Dict[str, dict]) -> None:
    """ Make sure this is a dict of dicts (not loaded from arbitrary JSON/INI files). """
    if not all([type(v) is dict for v in d.values()]):
        raise TypeError("All first-level values in an index or config file must be dicts.")
