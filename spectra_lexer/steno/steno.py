""" The primary steno analysis engine. Generates rules from translations and creates visual representations. """

from functools import partial
from itertools import product
import os
from typing import Dict, Iterable, List, Tuple

from .analyzer import StenoAnalyzer
from .base import LX
from .board import BoardGenerator
from .codec import cson_decode, cfg_decode, cfg_encode, json_decode, json_encode
from .graph import GraphGenerator, StenoGraph
from .lexer import StenoLexer
from .resource import KeyLayout, RuleParser, StenoRule
from .search import SearchEngine
from .view import ViewProcessor
from spectra_lexer.system import SystemLayer


class StenoEngine(LX):
    """ Component to load all resources necessary for a steno system. The structures are mostly JSON dicts.
        Assets including a key layout, rules, and (optional) board graphics comprise the system.
        Other files from user space include a translations dictionary and examples index. """

    index_file: str = ""   # Holds filename for index; set on first load.
    config_file: str = ""  # Holds filename for config; set on first load.

    _rule_parser: RuleParser   # Parses rules from JSON and keeps track of the references for inverse parsing.
    _view: ViewProcessor

    _board: BoardGenerator = None
    _grapher: GraphGenerator = None
    _lexer: StenoLexer = None
    _analyzer: StenoAnalyzer = None
    _search: SearchEngine = None

    def __init__(self, system:SystemLayer):
        self._read = system.read
        self._read_all = system.read_all
        self._write = system.write
        self._rule_parser = RuleParser()
        self._view = ViewProcessor(self)

    def RSSystemLoad(self, base_dir:str) -> dict:
        """ Given a base directory, load each steno system component by a standard name or pattern. """
        with_path = partial(os.path.join, base_dir)
        d = {"layout":      self._load_layout(with_path("layout.json")),          # Steno key constants.
             "rules":       self._load_rules(with_path("*.cson")),                # CSON rules glob pattern.
             "board_defs":  self._load_board_defs(with_path("board_defs.json")),  # Board shape definitions.
             "board_xml":   self._load_board_xml(with_path("board_elems.xml"))}   # XML steno board elements.
        self.RSSystemReady(**d)
        return d

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

    def RSSystemReady(self, layout:KeyLayout, rules:Dict[str, StenoRule],
                      board_defs:dict, board_xml:bytes) -> None:
        """ Send this command with all system resources as keywords. """
        self._board = BoardGenerator(layout, rules, board_defs, board_xml)
        self._grapher = GraphGenerator(layout)
        self._lexer = StenoLexer(layout, rules)
        self._analyzer = StenoAnalyzer(self._lexer, rules)
        self._search = SearchEngine(rules)

    def RSRulesSave(self, rules:Iterable[StenoRule], filename:str="") -> None:
        """ Parse a rules dictionary back into raw form and save it to JSON. """
        raw_dict = self._rule_parser.compile_to_raw(rules)
        self._write(json_encode(raw_dict), filename)

    def RSTranslationsLoad(self, *patterns:str) -> Dict[str, str]:
        """ Load and merge translations from disk. Ignore missing files. """
        translations = {}
        for data in self._read_all(*patterns):
            d = json_decode(data)
            translations.update(d)
        self.RSTranslationsReady(translations)
        return translations

    def RSTranslationsSave(self, translations:Dict[str, str], filename:str="") -> None:
        """ Save a translations dict directly into JSON. """
        self._write(json_encode(translations), filename)

    def RSTranslationsReady(self, translations:Dict[str, str]) -> None:
        """ Send this command with the new translations dict for all components. """
        self._search.load_translations(translations)
        self._analyzer.load(translations.items())

    def RSIndexLoad(self, filename:str) -> Dict[str, dict]:
        """ Load an index from disk. Ignore missing files. """
        self.index_file = filename
        index = json_decode(self._read(filename))
        self.RSIndexReady(index)
        return index

    def RSIndexSave(self, index:Dict[str, dict], filename:str="") -> None:
        """ Save an index structure directly into JSON. If no save filename is given, use the default. """
        self._write(json_encode(index), filename or self.index_file)

    def RSIndexReady(self, index:Dict[str, dict]) -> None:
        """ Send this command with the new index for all components. """
        self._search.load_index(index)

    def RSConfigLoad(self, filename:str) -> Dict[str, dict]:
        """ Load config settings from disk. Ignore missing files. """
        self.config_file = filename
        cfg = cfg_decode(self._read(filename))
        self.RSConfigReady(cfg)
        return cfg

    def RSConfigSave(self, cfg:Dict[str, dict], filename:str="") -> None:
        """ Save a config dict into .cfg format. """
        self._write(cfg_encode(cfg), filename or self.config_file)

    def RSConfigReady(self, cfg:Dict[str, dict]) -> None:
        """ Send this command with the new config dict for all components. """
        self._view.load_config(cfg)

    def LXLexerQuery(self, keys:str, word:str, **kwargs) -> StenoRule:
        """ Return and send out the best rule that maps the given key string to the given word. """
        return self._lexer.query(keys, word, **kwargs)

    def LXLexerQueryProduct(self, keys:Iterable[str], words:Iterable[str], **kwargs) -> StenoRule:
        """ As arguments, take iterables of keys and words and test every possible pairing.
            Return and send out the best rule out of all combinations. """
        return self._lexer.query_best(product(keys, words), **kwargs)

    def LXAnalyzerMakeRules(self, *args, **kwargs) -> List[StenoRule]:
        """ Make a new rules list by running the lexer in parallel on all currently loaded translations. """
        return self._analyzer.make_rules(*args, **kwargs)

    def LXAnalyzerMakeIndex(self, *args) -> Dict[str, dict]:
        """ Generate a set of rules from translations using the lexer and compare them to the built-in rules.
            Make a index for each built-in rule containing a dict of every translation that used it. """
        return self._analyzer.make_index(*args)

    def LXGraphGenerate(self, rule:StenoRule, **kwargs) -> StenoGraph:
        """ Generate text graph data from a rule. """
        return self._grapher(rule, **kwargs)

    def LXBoardFromKeys(self, keys:str, *args) -> bytes:
        """ Generate encoded board diagram layouts arranged according to <aspect_ratio> from a set of steno keys. """
        return self._board.from_keys(keys, *args)

    def LXBoardFromRule(self, rule:StenoRule, *args) -> bytes:
        """ Generate encoded board diagram layouts arranged according to <aspect_ratio> from a steno rule. """
        return self._board.from_rule(rule, *args)

    def LXSearchQuery(self, *args, **kwargs) -> List[str]:
        """ Choose an index to use based on delimiters in the input pattern.
            Search for matches in that index. If <match> is given, the search will find mappings instead. """
        return self._search.search(*args, **kwargs)

    def LXSearchFindExample(self, *args, **kwargs) -> Tuple[str, str]:
        """ Find an example translation in the index for the given link and return it with the required input text. """
        return self._search.find_example(*args, **kwargs)

    def LXSearchFindLink(self, rule:StenoRule) -> str:
        """ Return the name of the given rule to use in a link, but only if it has examples in the index. """
        return self._search.rule_to_link(rule)

    def LXSearchFindRule(self, link:str) -> StenoRule:
        """ Return the rule under the given link name, or None if there is no rule by that name. """
        return self._search.link_to_rule(link)

    def VIEWAction(self, state:dict, action:str) -> dict:
        """ Perform an action with the given state dict, then return it with the changes. """
        return self._view.process(state, action)
