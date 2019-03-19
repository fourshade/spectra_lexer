#!/usr/bin/env python3

""" Main test module for the Spectra steno lexer. Currently handles all major components except the GUI. """

from itertools import starmap
import re

import pytest

from spectra_lexer.app import Application
from spectra_lexer.core.file import FileHandler
from spectra_lexer.plover import PloverTranslationsParser
from spectra_lexer.plover.compat import PloverStenoDictCollection
from spectra_lexer.steno import *
from spectra_lexer.steno.rules import RuleFlags
from test import get_test_filename


# Create and connect components for the tests in order as we need them.
# Some will need access to the file system. They only need to send engine commands for this, not receive them.
FILE_ENGINE = Application(FileHandler)
RULES = RulesManager()
RULES.engine_connect(FILE_ENGINE.call)
RULES_DICT = RULES.load()


@pytest.mark.parametrize("r", RULES_DICT.values())
def test_rules(r):
    """ Go through each rule and perform extensive integrity checks. """
    # If the entry has flags, verify that all of them are valid.
    if r.flags:
        bad_flags = r.flags - RuleFlags.values
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
TRANSLATIONS.engine_connect(FILE_ENGINE.call)
TRANSLATIONS_DICT = TRANSLATIONS.load([get_test_filename("translations")])
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


INDEX = IndexManager()
INDEX.engine_connect(FILE_ENGINE.call)
INDEX_DICT = INDEX.load(get_test_filename("index"))
TEST_INDEX = list(INDEX_DICT.items())
SEARCH = SearchEngine()
SEARCH.set_rules(RULES_DICT)
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
    all_keys = set(rule.keys.rtfcre) - set("/-")
    assert all_keys == all_keys.intersection(*kresults)


SVG = SVGManager()
SVG.engine_connect(FILE_ENGINE.call)
SVG_PARAMS = SVG.load()
BOARD = BoardRenderer()
BOARD.set_board(*SVG_PARAMS)
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
    root = GRAPH._locator.select(0, 0)
    assert root.parent is None
    # Every other node descends from it and is unique.
    all_nodes_list = root.get_descendents()
    all_nodes_set = set(all_nodes_list)
    assert len(all_nodes_list) == len(all_nodes_set)
    # Going the other direction, all nodes except the root must have its parent in the set.
    assert all([node.parent in all_nodes_set for node in all_nodes_list[1:]])
    # The nodes available for interaction must be a subset of this collection.
    assert all_nodes_set >= set(GRAPH._formatter)


PLOVER = PloverTranslationsParser()


def test_plover():
    """ Make sure the Plover interface can convert dicts between tuple-based keys and string-based keys. """
    test_dc = PloverStenoDictCollection(TRANSLATIONS_DICT, split_count=3)
    assert len(PLOVER.load_dicts(test_dc)) == len(TRANSLATIONS_DICT)
