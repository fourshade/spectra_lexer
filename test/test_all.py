#!/usr/bin/env python3

""" Main test module for the Spectra steno lexer. Currently handles all major components except the GUI. """

from itertools import starmap
import re

import pytest

from spectra_lexer import Component
from spectra_lexer.core.file import FileHandler
from spectra_lexer.core.lexer import StenoLexer
from spectra_lexer.core.rules import RulesManager
from spectra_lexer.core.translations import TranslationsManager
from spectra_lexer.interactive.board import BoardRenderer
from spectra_lexer.interactive.graph import GraphRenderer
from spectra_lexer.interactive.search import SearchEngine
from spectra_lexer.plover.compat import PloverEngine, PloverStenoDictCollection
from spectra_lexer.plover.interface import PloverInterface
from spectra_lexer.rules import RuleFlags
from test import get_test_filename


def direct_connect(cmp:Component, subcmp:Component) -> None:
    """ Connect one component directly to another without an engine for basic calls.
        Only works with components that have no duplicate command keys. """
    cmd_dict = dict(subcmp.engine_commands())
    def direct_call(cmd:str, *args, **kwargs) -> callable:
        c = cmd_dict.get(cmd)
        if c:
            return c[0](*args, **kwargs)
    cmp.engine_connect(direct_call)


# Create components for the tests in order as we need them.
FILE = FileHandler()
RULES = RulesManager()
direct_connect(RULES, FILE)
RULES_DICT = RULES.load()


@pytest.mark.parametrize("r", RULES_DICT.values())
def test_rules(r):
    """ Go through each rule and perform extensive integrity checks. """
    # If the entry has flags, verify that all of them are valid.
    if r.flags:
        bad_flags = r.flags - RuleFlags
        assert not bad_flags, f"Entry {r} has illegal flag(s): {bad_flags}"
    # A rule with children in a rulemap must conform to strict rules for successful parsing.
    # These tests only work for rules that do not allow the same key to appear in two different strokes.
    if r.rulemap:
        child_key_sets = [set(cr.rule.keys) for cr in r.rulemap]
        combined_child_keys = set()
        # Make sure none of the child rules have overlapping keys.
        for s in child_key_sets:
            conflicts = combined_child_keys & s
            assert not conflicts, f"Entry {r} has child rules with overlapping keys: {conflicts}"
            combined_child_keys |= s
        # Make sure the child rules contain all the keys of the parent between them (and no extras).
        key_diff = set(r.keys) ^ combined_child_keys
        assert not key_diff, f"Entry {r} has mismatched keys vs. its child rules: {key_diff}"


TRANSLATIONS = TranslationsManager()
direct_connect(TRANSLATIONS, FILE)
TRANSLATIONS_DICT = TRANSLATIONS.load([get_test_filename()])
TEST_TRANSLATIONS = list(TRANSLATIONS_DICT.items())
LEXER = StenoLexer()
LEXER.set_rules(RULES_DICT)
LEXER.need_all_keys = True
TEST_RESULTS = list(starmap(LEXER.query, TEST_TRANSLATIONS))


@pytest.mark.parametrize("result", TEST_RESULTS)
def test_lexer(result):
    """ The parsing tests fail if the parser can't match all the keys. """
    rulemap = result.rulemap
    assert rulemap, f"Lexer failed to match all keys on {result.keys} -> {result.letters}."


SEARCH = SearchEngine()
SEARCH.set_translations(TRANSLATIONS_DICT)


@pytest.mark.parametrize("trial", TEST_TRANSLATIONS)
def test_search(trial):
    """ Go through each loaded test translation and check the search engine in all modes. """
    keys, word = trial
    # Search should return a one-item list with that item selected for both keys and word in either mode.
    SEARCH.reset()
    assert SEARCH.on_input(word) == ([word], word)
    SEARCH.set_mode_strokes(True)
    assert SEARCH.on_input(keys) == ([keys], keys)
    SEARCH.set_mode_regex(True)
    assert SEARCH.on_input(re.escape(keys)) == ([keys], keys)
    SEARCH.set_mode_strokes(False)
    assert SEARCH.on_input(re.escape(word)) == ([word], word)


BOARD = BoardRenderer()
direct_connect(BOARD, FILE)
BOARD_DICT = BOARD.load()
BOARD.set_rules(RULES_DICT)
BOARD.set_layout((0, 0, 100, 100), 100, 100)


@pytest.mark.parametrize("result", TEST_RESULTS)
def test_board(result):
    """ Perform all tests for board diagram output. Currently only checks that the output isn't empty. """
    assert BOARD.get_info(result)


GRAPH = GraphRenderer()


@pytest.mark.parametrize("result", TEST_RESULTS)
def test_graph(result):
    """ Perform all tests for text graph output. Mainly limited to examining the node tree for consistency. """
    GRAPH.generate(result)
    # The root node starts in the upper left and has no parent.
    root = GRAPH._graph._locator.select(0, 0)
    assert root.parent is None
    # Every other node descends from it and is unique.
    all_nodes_list = root.get_descendents()
    all_nodes_set = set(all_nodes_list)
    assert len(all_nodes_list) == len(all_nodes_set)
    # Going the other direction, all nodes except the root must have its parent in the set.
    assert all([node.parent in all_nodes_set for node in all_nodes_list[1:]])
    # The nodes available for interaction must be a subset of this collection.
    assert all_nodes_set >= set(GRAPH._graph._formatter)


PLOVER = PloverInterface()
PLOVER.start(plover_engine=PloverEngine())


def test_plover():
    """ Make sure the Plover interface can convert dicts between tuple-based keys and string-based keys. """
    test_dc = PloverStenoDictCollection(TRANSLATIONS_DICT, split_count=3)
    assert len(PLOVER.parse_dicts(test_dc)) == len(TRANSLATIONS_DICT)
