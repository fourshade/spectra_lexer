from typing import Dict

from .board import BoardEngine, BoardElementParser
from .engine import StenoEngine
from .graph import GraphEngine
from .keys import KeyLayout
from .lexer import CompoundRuleMatcher, PrefixMatcher, SpecialMatcher, StenoLexer, StrokeMatcher, WordMatcher
from .rules import RuleCollection


class StenoEngineFactory:
    """ Contains all static resources (loaded from package assets) necessary for a steno system.
        The structures are all JSON dicts. Assets include a key layout, rules, and board graphics. """

    # These are the acceptable string values for lexer flags, as read from JSON.
    _SPECIAL = "SPEC"  # Special rule used internally (in other rules). Only referenced by name.
    _STROKE = "STRK"   # Exact match for a single stroke, not part of one. Handled by exact dict lookup.
    _WORD = "WORD"     # Exact match for a single word. These rules do not adversely affect lexer performance.
    _RARE = "RARE"     # Rule applies to very few words and could specifically cause false positives.

    # These are the acceptable string values for graph and board element flags, as read from JSON.
    _INVERSION = "INV"  # Inversion of steno order. A transposition symbol will be added.
    _LINKED = "LINK"    # Rule that uses keys from two strokes. A linking symbol will be added.

    # Some rules have hard-coded behavior in the lexer to match special case uses of the asterisk.
    _SPECIALS = [(SpecialMatcher.add_rule_abbreviation, "may indicate an abbreviation"),
                 (SpecialMatcher.add_rule_proper,       "may indicate a proper noun\n(names, places, etc.)"),
                 (SpecialMatcher.add_rule_affix,        "may indicate a prefix or suffix stroke"),
                 (SpecialMatcher.add_rule_fallback,     "purpose unknown\nPossibly resolves a conflict")]

    def __init__(self, layout:KeyLayout, rules:RuleCollection, board_defs:Dict[str, dict]) -> None:
        self._layout = layout          # Converts between user RTFCRE steno strings and s-keys.
        self._rules = rules            # Collection of steno rules with data for all components.
        self._board_defs = board_defs  # Dict with various parameters for stneo board rendering.

    def build_lexer(self) -> StenoLexer:
        rules = self._rules
        key_sep = self._layout.sep
        key_special = self._layout.special
        prefix_matcher = PrefixMatcher(key_sep, self._layout.unordered)
        stroke_matcher = StrokeMatcher(key_sep)
        word_matcher = WordMatcher()
        rare_rules = []
        for rule in rules:
            # Special rules are only used internally.
            flags = rule.flags
            if self._SPECIAL not in flags:
                # Add each steno rule to one of the rule matchers by name based on its flags.
                # Rules are added to the tree-based prefix matcher by default.
                matcher = prefix_matcher
                if self._STROKE in flags:
                    # Stroke rules are matched only by complete strokes.
                    matcher = stroke_matcher
                elif self._WORD in flags:
                    # Word rules are matched only by whole words (but still case-insensitive).
                    matcher = word_matcher
                name = rule.name
                skeys = self._layout.from_rtfcre(rule.keys)
                matcher.add(name, skeys, rule.letters)
                if self._RARE in flags:
                    # Rare rules are uncommon in usage and/or prone to causing false positives.
                    # They are worth less when deciding the most accurate rule map.
                    rare_rules.append(name)
        special_matcher = SpecialMatcher(key_sep, key_special)
        for matcher_add, desc in self._SPECIALS:
            rule = rules.make_special(key_special, desc)
            matcher_add(special_matcher, rule.name)
        matcher = CompoundRuleMatcher(prefix_matcher, stroke_matcher, word_matcher, special_matcher)
        return StenoLexer(matcher, rare_rules)

    def build_board_engine(self) -> BoardEngine:
        board_parser = BoardElementParser(self._board_defs)
        for rule in self._rules:
            name = rule.name
            skeys = self._layout.from_rtfcre(rule.keys)
            flags = rule.flags
            is_inversion = self._INVERSION in flags
            is_linked = self._LINKED in flags
            board_parser.add_rule(name, skeys, is_inversion, is_linked)
            for item in rule.rulemap:
                board_parser.add_connection(name, item.name)
        return board_parser.build_engine()

    def build_graph_engine(self) -> GraphEngine:
        key_sep = self._layout.sep
        graph_engine = GraphEngine()
        for rule in self._rules:
            name = rule.name
            keys = rule.keys
            flags = rule.flags
            rulemap = rule.rulemap
            is_separator = (keys == key_sep)
            is_inversion = self._INVERSION in flags
            is_linked = self._LINKED in flags
            graph_engine.add_rule(name, keys, rule.letters, rule.description,
                                  is_separator, is_inversion, is_linked)
            for item in rulemap:
                graph_engine.add_connection(name, item.name, item.start, item.length)
        return graph_engine

    def build_engine(self) -> StenoEngine:
        lexer = self.build_lexer()
        board_engine = self.build_board_engine()
        graph_engine = self.build_graph_engine()
        return StenoEngine(self._layout, lexer, board_engine, graph_engine)
