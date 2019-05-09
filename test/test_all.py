#!/usr/bin/env python3

""" Main test module for the Spectra steno lexer. Currently handles all major components except the GUI. """

from collections import Counter
from itertools import starmap
import re

import pytest

from spectra_lexer.plover import PloverCompatibilityLayer
from spectra_lexer.steno import IndexManager, TranslationsManager
from spectra_lexer.steno.board import BoardRenderer
from spectra_lexer.steno.graph import GraphRenderer
from spectra_lexer.steno.lexer import StenoLexer
from spectra_lexer.steno.rules import RuleFlags
from spectra_lexer.steno.search import SearchEngine
from spectra_lexer.steno.system import SystemManager
from test import get_test_filename


# Create and connect components for the tests in order as we need them.
SYSTEM = SystemManager()
SYSTEM_OBJ = SYSTEM.load()
RULES_DICT = SYSTEM_OBJ.rules
IGNORED_KEYS = Counter({"/": 999, "-": 999})


@pytest.mark.parametrize("r", RULES_DICT.values())
def test_rules(r):
    """ Go through each rule and perform extensive integrity checks. """
    # If the entry has flags, verify that all of them are valid.
    if r.flags:
        bad_flags = r.flags - RuleFlags.values
        assert not bad_flags, f"Entry {r} has illegal flag(s): {bad_flags}"
    # Make sure the child rules contain all the keys of the parent between them, and no extras.
    if r.rulemap:
        keys = Counter(r.keys)
        keys.subtract(Counter([k for cr in r.rulemap for k in cr.rule.keys]))
        keys -= IGNORED_KEYS
        assert not keys, f"Entry {r} has mismatched keys vs. its child rules: {list(keys)}"


TRANSLATIONS = TranslationsManager()
TRANSLATIONS_DICT = TRANSLATIONS.load(get_test_filename("translations"))
TEST_TRANSLATIONS = list(TRANSLATIONS_DICT.items())
LEXER = StenoLexer()
LEXER.set_system(SYSTEM_OBJ)
LEXER.need_all_keys = True
TEST_RESULTS = list(starmap(LEXER.query, TEST_TRANSLATIONS))


@pytest.mark.parametrize("result", TEST_RESULTS)
def test_lexer(result):
    """ The parsing tests fail if the parser can't match all the keys. """
    rulemap = result.rulemap
    assert rulemap, f"Lexer failed to match all keys on {result.keys} -> {result.letters}."


INDEX = IndexManager()
INDEX_DICT = INDEX.load(get_test_filename("index"))
TEST_INDEX = list(INDEX_DICT.items())
SEARCH = SearchEngine()
SEARCH.set_rules(SYSTEM_OBJ.rules)
SEARCH.set_translations(TRANSLATIONS_DICT)
SEARCH.set_index(INDEX_DICT)


@pytest.mark.parametrize("trial", TEST_TRANSLATIONS)
def test_search(trial):
    """ Go through each loaded test translation and check the search engine in all modes. """
    keys, word = trial
    # For both keys and word, and in either mode, search should return a list with only the item itself.
    assert SEARCH.search(word) == [word]
    SEARCH.set_mode_strokes(True)
    assert SEARCH.search(keys) == [keys]
    SEARCH.set_mode_regex(True)
    assert SEARCH.search(re.escape(keys)) == [keys]
    SEARCH.set_mode_strokes(False)
    assert SEARCH.search(re.escape(word)) == [word]
    SEARCH.set_mode_regex(False)


def test_rules_search():
    """ A rules prefix search with no body should return every rule we have after expanding it all we can. """
    results = SEARCH.search("/")
    while "(more...)" in results:
        SEARCH._add_page_to_count()
        results = SEARCH._repeat_search()
    assert len(results) == len(RULES_DICT)


@pytest.mark.parametrize("trial", TEST_INDEX)
def test_index_search(trial):
    # Any rule with translations in the index should have its keys and letters somewhere in every entry.
    rname, tdict = trial
    rule = RULES_DICT[rname]
    wresults = SEARCH.search(f"//{rname}")
    assert all([rule.letters in r for r in wresults])
    SEARCH.set_mode_strokes(True)
    kresults = SEARCH.search(f"//{rname}")
    SEARCH.set_mode_strokes(False)
    all_keys = set(rule.keys) - set("/-")
    assert all_keys == all_keys.intersection(*kresults)


BOARD = BoardRenderer()
BOARD.set_system(SYSTEM_OBJ)
BOARD.set_size(100, 100)


@pytest.mark.parametrize("result", TEST_RESULTS)
def test_board(result):
    """ Perform all tests for board diagram output. Currently only checks that the output doesn't raise. """
    BOARD.display_rule(result)


GRAPH = GraphRenderer()
GRAPH.layout = SYSTEM_OBJ.layout


@pytest.mark.parametrize("result", TEST_RESULTS)
def test_graph(result):
    """ Perform all tests for text graph output. Mainly limited to examining the node tree for consistency. """
    GRAPH.generate(result)
    # The root node uses the top-level rule and has no parent.
    root = GRAPH._organizer.node_from(result)
    assert root.parent is None
    # Every other node descends from it and is unique.
    child_nodes_list = list(root.descendents())
    child_nodes_set = set(child_nodes_list)
    assert len(child_nodes_list) == len(child_nodes_set)
    # Going the other direction, all nodes except the root must have its parent in the set.
    all_nodes_set = child_nodes_set | {root}
    assert all([node.parent in all_nodes_set for node in child_nodes_list])
    # The nodes available for interaction must be a subset of our collection.
    assert all_nodes_set >= set(GRAPH._formatter._sections)


PLOVER = PloverCompatibilityLayer()


def test_plover():
    """ Make sure the Plover interface can convert dicts between tuple-based keys and string-based keys. """
    test_dc = PLOVER.fake_engine(TRANSLATIONS_DICT, split_count=3).dictionaries
    assert len(PLOVER.convert_dicts(test_dc)) == len(TRANSLATIONS_DICT)
