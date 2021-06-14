from spectra_lexer.board.layout import GridLayoutEngine
from spectra_lexer.board.tfrm import TextTransformer
from spectra_lexer.lexer.composite import PriorityRuleMatcher
from spectra_lexer.lexer.exact import StrokeMatcher, WordMatcher
from spectra_lexer.lexer.lexer import LexerRule, StenoLexer
from spectra_lexer.lexer.prefix import UnorderedPrefixMatcher
from spectra_lexer.lexer.special import DelimiterMatcher, SpecialMatcher
from spectra_lexer.options import SpectraOptions
from spectra_lexer.resource.board import FillColors, StenoBoardDefinitions
from spectra_lexer.resource.keys import converter_from_keymap, StenoKeyConverter, StenoKeyLayout
from spectra_lexer.resource.rules import StenoRuleFactory
from spectra_lexer.spc_board import BoardEngine, SVGBoardFactory
from spectra_lexer.spc_graph import GraphEngine
from spectra_lexer.spc_lexer import StenoAnalyzer
from spectra_lexer.spc_resource import StenoResourceIO, StenoRuleList
from spectra_lexer.spc_search import SearchEngine
from spectra_lexer.util.log import open_logger, StreamLogger


class Spectra:
    """ Container/factory for all common components, and the basis for using Spectra as a library. """

    def __init__(self, opts:SpectraOptions=None, *, parse_args=True) -> None:
        """ Start with the bare minimum of components and create the rest on demand. """
        if opts is None:
            opts = SpectraOptions()
        if parse_args:
            opts.parse()
        self._opts = opts
        self.translations_paths = opts.translations_paths()
        self.index_path = opts.index_path()
        self.cfg_path = opts.config_path()

    class Component:
        """ Property-like descriptor to create a component if it does not exist, then save it over the attribute. """

        def __init__(self, func) -> None:
            self._func = func

        def __get__(self, instance, owner=None) -> object:
            value = self._func(instance)
            setattr(instance, self._func.__name__, value)
            return value

    @Component
    def logger(self) -> StreamLogger:
        """ Open a thread-safe logger that writes to both stdout and a log file. """
        log_path = self._opts.log_path()
        return open_logger(log_path, to_stdout=True)

    @Component
    def _rule_factory(self) -> StenoRuleFactory:
        """ Rules are the most highly coupled data type; they need their own factory to keep things sane. """
        return StenoRuleFactory()

    @Component
    def resource_io(self) -> StenoResourceIO:
        """ Build the loader for JSON file-based resources. """
        rule_factory = self._rule_factory
        return StenoResourceIO(rule_factory)

    @Component
    def keymap(self) -> StenoKeyLayout:
        """ Load and verify the built-in key layout. """
        keymap_path = self._opts.keymap_path()
        keymap = self.resource_io.load_keymap(keymap_path)
        keymap.verify()
        return keymap

    @Component
    def _key_converter(self) -> StenoKeyConverter:
        """ Build a formatter to convert between dictionary and lexer key formats. """
        return converter_from_keymap(self.keymap)

    @Component
    def rules(self) -> StenoRuleList:
        """ Load and verify the built-in steno rules. """
        rules_path = self._opts.rules_path()
        rules = self.resource_io.load_rules(rules_path)
        keymap = self.keymap
        delimiters = {keymap.sep, keymap.split}
        valid_rtfcre = delimiters.union(keymap.left, keymap.center, keymap.right)
        for rule in rules:
            rule.verify(valid_rtfcre, delimiters)
        return rules

    @Component
    def board_defs(self) -> StenoBoardDefinitions:
        """ Load and verify the built-in board diagram definitions. """
        board_defs_path = self._opts.board_defs_path()
        board_defs = self.resource_io.load_board_defs(board_defs_path)
        board_defs.verify()
        return board_defs

    @Component
    def search_engine(self) -> SearchEngine:
        """ For stroke-based searches, hyphens should be stripped off each end. """
        ws = " \r\n\t"
        strip_strokes = self.keymap.split + ws
        strip_text = ws
        return SearchEngine(strip_strokes, strip_text)

    @Component
    def analyzer(self) -> StenoAnalyzer:
        """ Distribute rules and build the rule matchers, lexer and analyzer. """
        refmap = {}
        matcher_groups = []
        rule_factory = self._rule_factory
        keymap = self.keymap
        converter = self._key_converter
        rules = self.rules
        key_sep = keymap.sep
        key_special = keymap.special

        # Separators are force-matched before the normal matchers can waste cycles on them.
        sep_matcher = DelimiterMatcher()
        lr_sep = LexerRule(key_sep, "", 0)
        rule_factory.push()
        rule_sep = rule_factory.build(key_sep, "", "stroke separator")
        refmap[lr_sep] = rule_sep
        sep_matcher.add(lr_sep)
        matcher_groups.append([sep_matcher])

        # Matchers for rules without special behavior are processed as one group.
        prefix_matcher = UnorderedPrefixMatcher(key_sep, key_special)
        stroke_matcher = StrokeMatcher(key_sep)
        word_matcher = WordMatcher()
        idmap = {}
        for rule in rules:
            # Convert each rule to lexer format. Rule weight is assigned based on letters matched.
            # Rare rules are uncommon in usage and/or prone to causing false positives.
            # They have slightly reduced weight so that other rules with equal letter count are chosen first.
            # Word rules may be otherwise equal to some prefixes and suffixes; they need *more* weight to win.
            skeys = converter.rtfcre_to_skeys(rule.keys)
            letters = rule.letters
            weight = 10 * len(letters) - rule.is_rare + rule.is_word
            lr = LexerRule(skeys, letters, weight)
            # Map every lexer-format rule to the original so we can convert back.
            refmap[lr] = rule
            # Rules without special behavior should be in example indices.
            idmap[lr] = rule.id
            # Add the lexer rule to one of the rule matchers based on flags.
            if rule.is_reference:
                # Reference-only rules are not matched directly.
                pass
            elif rule.is_stroke:
                # Stroke rules are matched only by complete strokes.
                stroke_matcher.add(lr)
            elif rule.is_word:
                # Word rules are matched only by whole words (but still case-insensitive).
                word_matcher.add(lr)
            else:
                # All other rules are added to the tree-based prefix matcher.
                prefix_matcher.add(lr)
        matcher_groups.append([prefix_matcher, stroke_matcher, word_matcher])

        # Use the special matcher only if absolutely nothing else has worked.
        special_matcher = SpecialMatcher(key_sep)
        for pred in SpecialMatcher.Predicate.LIST:
            # Rules with special behavior must be handled case-by-case.
            lr = LexerRule(key_special, "", 0)
            info = key_special + ": " + pred.desc
            rule_factory.push()
            rule = rule_factory.build(key_special, "", info, pred.repl)
            refmap[lr] = rule
            special_matcher.add_test(lr, pred)
        matcher_groups.append([special_matcher])

        # Each matcher group is tried in order of priority (separators first, specials last).
        matcher = PriorityRuleMatcher(*matcher_groups)
        lexer = StenoLexer(matcher)
        return StenoAnalyzer(converter, lexer, rule_factory, refmap, idmap)

    @Component
    def graph_engine(self) -> GraphEngine:
        """ The graph engine should ignore hyphens so that consecutive right-side keys are adjacent. """
        keymap = self.keymap
        key_sep = keymap.sep
        ignored_chars = {keymap.split}
        return GraphEngine(key_sep, ignored_chars)

    @Component
    def board_engine(self) -> BoardEngine:
        """ Set the base defintions with all single keys unlabeled. """
        keymap = self.keymap
        key_sep = keymap.sep
        key_combo = keymap.special
        converter = self._key_converter
        board_defs = self.board_defs
        key_procs = board_defs.keys
        rule_procs = board_defs.rules
        bg = FillColors(**board_defs.colors)
        text_tf = TextTransformer(**board_defs.font)
        factory = SVGBoardFactory(text_tf, board_defs.offsets, board_defs.shapes, board_defs.glyphs)
        layout = GridLayoutEngine(**board_defs.bounds)
        return BoardEngine(converter, key_sep, key_combo, key_procs, rule_procs, bg, factory, layout)
