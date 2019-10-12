from typing import Dict, Iterable, List, Tuple

from .analysis import IndexInfo, ParallelMapper
from .board import BoardElementParser, BoardEngine
from .caption import RuleCaptioner
from .graph import GraphEngine
from .keys import KeyLayout
from .lexer import LexerResult, StenoLexer
from .rules import IndexCompiler, InverseRuleParser, RuleParser, StenoRule
from .search import SearchEngine


class StenoEngine:
    """ Main access point for steno analysis. Generates rules from translations and creates visual representations. """

    def __init__(self, layout:KeyLayout, rule_parser:RuleParser, lexer:StenoLexer,
                 board_engine:BoardEngine, graph_engine:GraphEngine, captioner:RuleCaptioner,
                 search_engine:SearchEngine) -> None:
        self._layout = layout            # Converts between user RTFCRE steno strings and s-keys.
        self._rule_parser = rule_parser  # Parses rules from JSON.
        self._lexer = lexer
        self._board_engine = board_engine
        self._graph_engine = graph_engine
        self._captioner = captioner
        self._search_engine = search_engine
        self._all_translations = []
        self.set_index = search_engine.set_index  # Load a new example search index.
        self.search_translations = search_engine.search_translations
        self.search_examples = search_engine.search_examples
        self.has_examples = search_engine.has_examples
        self.find_example = search_engine.find_example

    def set_translations(self, translations:Dict[str, str]) -> None:
        """ Load a new translations search dict. Keep a copy of the items for bulk analysis. """
        self._all_translations = list(translations.items())
        self._search_engine.set_translations(translations)

    def run(self, keys:str, letters:str, *,
            select_ref:str, find_rule:bool, set_focus:bool, board_ratio:float, match_all_keys:bool,
            graph_compress:bool, graph_compat:bool, board_compound:bool):
        """ Run a lexer query and return everything necessary to update the user GUI state. """
        names, positions, lengths, unmatched_skeys = self.lexer_query(keys, letters, match_all_keys=match_all_keys)
        connections = list(zip(names, positions, lengths))
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
            caption = self._captioner.caption_lexer(names, unmatched_skeys)
        elif rule_name == 'UNMATCHED':
            caption = unmatched_keys + ": unmatched keys"
            names = []
        else:
            caption = self._captioner.caption_rule(rule_name)
            names = [rule_name]
            unmatched_skeys = ""
        xml = self._board_engine.from_rules(names, unmatched_skeys, board_ratio, compound=board_compound)
        return text, set_focus, rule_name, caption, xml

    def lexer_query(self, keys:str, letters:str, *, match_all_keys=False):
        """ Return the best rule matching <keys> to <letters>.
            If <match_all_keys> is True, do not return partial results. """
        # Thoroughly parse the key string into s-keys format first.
        skeys = self._layout.from_rtfcre(keys)
        result = self._lexer.query(skeys, letters)
        names = result.rule_names()
        positions = result.rule_positions()
        lengths = result.rule_lengths()
        unmatched_skeys = result.unmatched_skeys()
        if unmatched_skeys and match_all_keys:
            # If the best result has unmatched keys, return a fully unmatched result instead.
            names = positions = lengths = ()
            unmatched_skeys = skeys
        return names, positions, lengths, unmatched_skeys

    def lexer_best_strokes(self, keys_iter:Iterable[str], letters:str) -> str:
        """ Return the best (most accurate) set of strokes from <keys_iter> that matches <letters>.
            Prefer shorter strokes over longer ones on ties. """
        keys_list = sorted(keys_iter, key=len)
        tr_list = [(self._layout.from_rtfcre(keys), letters) for keys in keys_list]
        best_index = self._lexer.find_best_translation(tr_list)
        return keys_list[best_index]

    def make_rules(self, **kwargs) -> Dict[str, list]:
        """ Run the lexer on all translations and return a list of raw rules with all keys matched for saving. """
        translations_in = self._all_translations
        results = self._parallel_query(translations_in, **kwargs)
        inv_parser = InverseRuleParser()
        for (keys, letters), result in zip(translations_in, results):
            if not result.unmatched_skeys():
                inv_parser.add(keys, letters, result.rule_names(), result.rule_positions(), result.rule_lengths())
        return inv_parser.to_dict()

    def make_index(self, size:int, **kwargs) -> Dict[str, dict]:
        """ Make a index from a parallel lexer query operation. Use an input filter to control size. """
        info = IndexInfo(size)
        translations_in = info.filter_translations(self._all_translations)
        results = self._parallel_query(translations_in, **kwargs)
        compiler = IndexCompiler()
        for (keys, letters), result in zip(translations_in, results):
            if not result.unmatched_skeys():
                compiler.add(keys, letters, result.rule_names())
        return compiler.to_dict()

    def _parallel_query(self, translations:Iterable[Tuple[str, str]], **kwargs) -> Iterable[LexerResult]:
        """ Return tuples of keys, letters, and results from lexer queries on all <translations>. """
        tr_list = [(self._layout.from_rtfcre(keys), letters) for keys, letters in translations]
        mapper = ParallelMapper(self._lexer.query, **kwargs)
        return mapper.starmap(tr_list)


class StenoResources:
    """ Contains all static resources necessary for a steno system. The structures are all JSON dicts.
        Assets include a key layout, rules, and board graphics. """

    def __init__(self, raw_layout:dict, raw_rules:Dict[str, list],
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
        search_engine = self._build_search_engine()
        return StenoEngine(layout, rule_parser, lexer, board_engine, graph_engine, captioner, search_engine)

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
    def _build_captioner(rules:Iterable[StenoRule]) -> RuleCaptioner:
        captioner = RuleCaptioner()
        for rule in rules:
            captioner.add_rule(rule.name, rule.keys, rule.letters, rule.desc, rule.rulemap)
        return captioner

    @staticmethod
    def _build_search_engine() -> SearchEngine:
        return SearchEngine()
