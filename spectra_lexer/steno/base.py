from collections import defaultdict
from typing import Dict, Iterable, Tuple

from .board import BoardElementParser, BoardEngine
from .graph import GraphEngine
from .keys import KeyLayout
from .lexer import LexerResult, StenoLexer
from .parallel import ParallelMapper
from .rules import InverseRuleParser, RuleParser, StenoRule

_RAW_RULES_TP = Dict[str, list]
_TR_DICT_TP = Dict[str, str]


class _RuleCaptioner:

    def __init__(self) -> None:
        self._captions = {}

    def add_rule(self, name:str, keys:str, letters:str, desc:str, has_children:bool) -> None:
        """ Generate and add a plaintext caption for a rule. """
        if has_children and letters:
            # Derived rules (i.e. non-leaf nodes) show the complete mapping of keys to letters in their description.
            left_side = f"{keys} → {letters}"
        else:
            # Base rules (i.e. leaf nodes) display their keys to the left of their descriptions.
            left_side = keys
        self._captions[name] = f"{left_side}: {desc}"

    def caption_rule(self, name:str) -> str:
        """ Return the plaintext caption for a rule. """
        return self._captions[name]


class StenoEngine:
    """ Main access point for steno analysis. Generates rules from translations and creates visual representations. """

    def __init__(self, layout:KeyLayout, rule_parser:RuleParser, lexer:StenoLexer,
                 board_engine:BoardEngine, graph_engine:GraphEngine, captioner:_RuleCaptioner) -> None:
        self._layout = layout            # Converts between user RTFCRE steno strings and s-keys.
        self._rule_parser = rule_parser  # Parses rules from JSON.
        self._lexer = lexer
        self._board_engine = board_engine
        self._graph_engine = graph_engine
        self._captioner = captioner

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
        graph = self._graph_engine.make_graph(root, compressed=graph_compress, compat=graph_compat)
        if find_rule:
            node = root.find_from_rule_name(select_ref)
        else:
            node = graph.find_node_from_ref(select_ref)
        text = graph.render(node, intense=set_focus)
        # If nothing is selected, remove any focus and generate a board and caption for the root node by default.
        if node is None:
            node = root
            set_focus = False
        rule_name = node.rule_name()
        if node is root:
            caption = result.caption()
            names = result.rule_names()
        elif rule_name == 'UNMATCHED':
            caption = unmatched_keys + ": unmatched keys"
            names = []
        else:
            caption = self._captioner.caption_rule(rule_name)
            names = [rule_name]
            unmatched_skeys = ""
        xml = self._board_engine.from_rules(names, unmatched_skeys, board_ratio, compound=board_compound)
        return text, set_focus, rule_name, caption, xml

    def lexer_query(self, keys:str, letters:str, *, match_all_keys=False) -> LexerResult:
        """ Return the best rule matching <keys> to <letters>.
            If <match_all_keys> is True, do not return partial results. """
        # Thoroughly parse the key string into s-keys format first.
        skeys = self._layout.from_rtfcre(keys)
        result = self._lexer.query(skeys, letters)
        if match_all_keys and result.unmatched_skeys():
            # If the best result has unmatched keys, return a fully unmatched result instead.
            return LexerResult([skeys])
        return result

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


class StenoResources:
    """ Contains all static resources necessary for a steno system. The structures are all JSON dicts.
        Assets include a key layout, rules, and board graphics. """

    def __init__(self, raw_layout:dict, raw_rules:_RAW_RULES_TP,
                 board_defs:Dict[str, dict], board_elems:Dict[str, dict]) -> None:
        """ All fields are static resources loaded from package assets. """
        self.raw_layout = raw_layout
        self.raw_rules = raw_rules
        self.board_defs = board_defs
        self.board_elems = board_elems

    def build_engine(self) -> StenoEngine:
        """ Load all resources into steno components and create an engine with them. """
        layout = KeyLayout(**self.raw_layout)
        layout.verify()
        rule_parser = RuleParser(self.raw_rules)
        rules = rule_parser.to_list()
        lexer = self._build_lexer(layout, rules)
        board_engine = self._build_board_engine(layout, rules)
        graph_engine = self._build_graph_engine(rules)
        captioner = self._build_captioner(rules)
        return StenoEngine(layout, rule_parser, lexer, board_engine, graph_engine, captioner)

    @staticmethod
    def _build_lexer(layout:KeyLayout, rules:Iterable[StenoRule]) -> StenoLexer:
        lexer = StenoLexer(layout.sep, layout.unordered)
        for rule in rules:
            # Parse keys from each rule into the case-unique s-keys format first.
            name = rule.name
            skeys = layout.from_rtfcre(rule.keys)
            letters = rule.letters
            if rule.is_special:
                lexer.add_special_rule(name)
            elif rule.is_stroke:
                lexer.add_stroke_rule(name, skeys, letters)
            elif rule.is_word:
                lexer.add_word_rule(name, skeys, letters)
            elif rule.is_rare:
                lexer.add_rare_rule(name, skeys, letters)
            else:
                lexer.add_prefix_rule(name, skeys, letters)
        return lexer

    def _build_board_engine(self, layout:KeyLayout, rules:Iterable[StenoRule]) -> BoardEngine:
        board_parser = BoardElementParser(self.board_defs)
        for rule in rules:
            name = rule.name
            skeys = layout.from_rtfcre(rule.keys)
            child_names = [item.name for item in rule.rulemap]
            board_parser.add_rule(name, skeys, child_names)
            if rule.is_linked:
                board_parser.set_rule_linked(name)
            elif rule.is_inversion:
                board_parser.set_rule_inversion(name)
        board_parser.parse(self.board_elems)
        return board_parser.build_engine()

    @staticmethod
    def _build_graph_engine(rules:Iterable[StenoRule]) -> GraphEngine:
        graph_engine = GraphEngine()
        for rule in rules:
            name = rule.name
            keys = rule.keys
            letters = rule.letters
            # Derived rules (i.e. branch nodes) show their letters.
            if rule.is_inversion:
                graph_engine.add_inversion_node(name, letters)
            elif rule.is_linked:
                graph_engine.add_linked_node(name, letters)
            elif rule.rulemap:
                graph_engine.add_branch_node(name, letters)
            # Base rules (i.e. leaf nodes) show their keys.
            elif rule.is_separator:
                graph_engine.add_separator_node(name, keys)
            else:
                graph_engine.add_leaf_node(name, keys)
            for item in rule.rulemap:
                graph_engine.add_connection(name, item.name, item.start, item.length)
        return graph_engine

    @staticmethod
    def _build_captioner(rules:Iterable[StenoRule]) -> _RuleCaptioner:
        captioner = _RuleCaptioner()
        for rule in rules:
            captioner.add_rule(rule.name, rule.keys, rule.letters, rule.desc, rule.rulemap)
        return captioner
