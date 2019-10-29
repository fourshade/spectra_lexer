from collections import defaultdict
from operator import methodcaller
from typing import Dict, Iterable, Tuple

from .board import BoardElementParser, BoardEngine
from .graph import GraphEngine
from .keys import KeyLayout
from .lexer import LexerResult, StenoLexer, StenoLexerFactory
from .parallel import ParallelMapper
from .rules import InverseRuleParser, RuleParser

_RAW_RULES_TP = Dict[str, list]
_TR_DICT_TP = Dict[str, str]


class StenoEngine:
    """ Main access point for steno analysis. Generates rules from translations and creates visual representations. """

    def __init__(self, layout:KeyLayout, lexer:StenoLexer,
                 board_engine:BoardEngine, graph_engine:GraphEngine, captions:Dict[str, str]) -> None:
        self._layout = layout  # Converts between user RTFCRE steno strings and s-keys.
        self._lexer = lexer
        self._board_engine = board_engine
        self._graph_engine = graph_engine
        self._captions = captions

    def run(self, keys:str, letters:str, *,
            select_ref:str, find_rule:bool, set_focus:bool, board_ratio:float, match_all_keys:bool,
            graph_compress:bool, graph_compat:bool, board_compound:bool):
        """ Run a lexer query and return everything necessary to update the user GUI state. """
        result = self.lexer_query(keys, letters, match_all_keys=match_all_keys)
        unmatched_skeys = result.unmatched_skeys()
        connections = list(result)
        # Convert unmatched keys back to RTFCRE format for the graph and caption.
        unmatched_keys = self._layout.to_rtfcre(unmatched_skeys)
        root = self._graph_engine.make_tree(letters, connections, unmatched_keys)
        target = None
        find_fn = methodcaller("rule_name" if find_rule else "ref")
        for node in root:
            if find_fn(node) == select_ref:
                target = node
                break
        text = root.render(target, compressed=graph_compress, compat=graph_compat, intense=set_focus)
        # If nothing is selected, remove any focus and generate a board and caption for the root node by default.
        if target is None:
            target = root
            set_focus = False
        rule_name = target.rule_name()
        if target is root:
            caption = result.caption()
            names = result.rule_names()
        elif rule_name == self._graph_engine.NAME_UNMATCHED:
            caption = unmatched_keys + ": unmatched keys"
            names = []
        else:
            caption = self._captions[rule_name]
            names = [rule_name]
            unmatched_skeys = ""
        xml = self._board_engine.from_rules(names, unmatched_skeys, board_ratio, compound=board_compound)
        return text, set_focus, rule_name, caption, xml

    def lexer_query(self, keys:str, letters:str, **kwargs) -> LexerResult:
        """ Return the best rule matching <keys> to <letters>. Thoroughly parse the key string into s-keys first. """
        skeys = self._layout.from_rtfcre(keys)
        return self._lexer.query(skeys, letters, **kwargs)

    def lexer_best_strokes(self, keys_iter:Iterable[str], letters:str) -> str:
        """ Return the best (most accurate) set of strokes from <keys_iter> that matches <letters>.
            Prefer shorter strokes over longer ones on ties. """
        keys_list = sorted(keys_iter, key=len)
        tr_list = [(self._layout.from_rtfcre(keys), letters) for keys in keys_list]
        best_index = self._lexer.find_best_translation(tr_list)
        return keys_list[best_index]

    def make_rules(self, translations:_TR_DICT_TP, **kwargs) -> _RAW_RULES_TP:
        """ Run the lexer on all <translations> and return a list of raw rules with all keys matched for saving. """
        inv_parser = InverseRuleParser()
        for keys, result in self._parallel_query(translations, **kwargs):
            inv_parser.add(keys, translations[keys], list(result))
        return inv_parser.to_dict()

    def make_index(self, translations:_TR_DICT_TP, **kwargs) -> Dict[str, _TR_DICT_TP]:
        """ Run the lexer on all <translations> and look at the top-level rule names.
            Make a index containing a dict for each built-in rule with every translation that used it. """
        index = defaultdict(dict)
        for keys, result in self._parallel_query(translations, **kwargs):
            letters = translations[keys]
            # Add a translation to the index under the name of every rule in the result.
            for name in result.rule_names():
                index[name][keys] = letters
        return index

    def _parallel_query(self, translations:_TR_DICT_TP, **kwargs) -> Iterable[Tuple[str, LexerResult]]:
        """ Return tuples of keys, letters, and results from complete lexer matches on <translations>. """
        tr_list = [(self._layout.from_rtfcre(keys), letters) for keys, letters in translations.items()]
        mapper = ParallelMapper(self._lexer.query, **kwargs)
        results = mapper.starmap(tr_list)
        return [(keys, result) for keys, result in zip(translations, results) if not result.unmatched_skeys()]


class StenoEngineFactory:
    """ Contains all static resources (loaded from package assets) necessary for a steno system.
        The structures are all JSON dicts. Assets include a key layout, rules, and board graphics. """

    def __init__(self, layout:KeyLayout, rule_parser:RuleParser,
                 board_defs:Dict[str, dict], board_elems:Dict[str, dict]) -> None:
        self.layout = layout            # Converts between user RTFCRE steno strings and s-keys.
        self.rule_parser = rule_parser  # Parses rules from JSON.
        self.board_defs = board_defs
        self.board_elems = board_elems

    def build_lexer(self) -> StenoLexer:
        factory = StenoLexerFactory(self.layout.sep, self.layout.unordered)
        for rule in self.rule_parser:
            # Parse keys from each rule into the case-unique s-keys format first.
            skeys = self.layout.from_rtfcre(rule.keys)
            factory.add_rule(rule.name, skeys, rule.letters, rule.flags)
        return factory.build()

    def build_board_engine(self) -> BoardEngine:
        board_parser = BoardElementParser(self.board_defs)
        board_parser.parse(self.board_elems)
        for rule in self.rule_parser:
            name = rule.name
            skeys = self.layout.from_rtfcre(rule.keys)
            board_parser.add_rule(name, skeys, rule.flags)
            for item in rule.rulemap:
                board_parser.add_connection(name, item.name)
        return board_parser.build_engine()

    def build_graph_engine(self) -> GraphEngine:
        graph_engine = GraphEngine(self.layout.sep)
        for rule in self.rule_parser:
            name = rule.name
            rulemap = rule.rulemap
            graph_engine.add_rule(name, rule.keys, rule.letters, rule.flags, bool(rulemap))
            for item in rulemap:
                graph_engine.add_connection(name, item.name, item.start, item.length)
        return graph_engine

    def build_captions(self) -> Dict[str, str]:
        return {rule.name: rule.caption for rule in self.rule_parser}
