#!/usr/bin/env python3

""" Main test module for the Spectra steno lexer. Currently handles all major components except the GUI. """

from collections import Counter
import re
import sys

import pytest

from spectra_lexer import StenoApplication
from spectra_lexer.plover.interface import PloverInterface
from spectra_lexer.plover.types import PloverEngine
from spectra_lexer.steno.search.index import StenoIndex
from spectra_lexer.steno.search.translations import TranslationsDictionary
from test import get_test_filename

# Load all resources using default command-line arguments and create components as we need them.
first, *rest = sys.argv
sys.argv = [first]
APP = StenoApplication()
sys.argv += rest
STENO = APP.steno
RULES_DICT = STENO._rule_parser._rules
IGNORED_KEYS = set("/-")


@pytest.mark.parametrize("r", RULES_DICT.values())
def test_rules(r):
    """ Go through each rule and perform extensive integrity checks. """
    flags = r.flags
    if flags:
        # If the entry has flags, verify that all of them are valid.
        bad_flags = flags.get_invalid()
        assert not bad_flags, f"Entry {r} has illegal flag(s): {bad_flags}"
    rulemap = r.rulemap
    if rulemap:
        # Check that the rulemap positions all fall within the legal bounds (i.e. within the parent's letters)
        # Make sure the child rules contain all the keys of the parent between them, and no extras.
        parent_len = len(r.letters)
        key_count = Counter(r.keys)
        for child, start, length in rulemap:
            assert start >= 0
            assert length >= 0
            assert start + length <= parent_len
            key_count.subtract(child.keys)
        mismatched = [k for k in key_count if key_count[k] and k not in IGNORED_KEYS]
        assert not mismatched, f"Entry {r} has mismatched keys vs. its child rules: {mismatched}"


TRANSLATIONS_DICT = TranslationsDictionary(STENO.RSTranslationsLoad(get_test_filename("translations")))
TEST_TRANSLATIONS = list(TRANSLATIONS_DICT.items())


@pytest.mark.parametrize("trial", TEST_TRANSLATIONS)
def test_translations_search(trial):
    """ Go through each loaded test translation and check the search method in all modes. """
    keys, word = trial
    # Search should return a list with only the item itself (or its value) in any mode.
    assert TRANSLATIONS_DICT.search(keys, count=2, strokes=True) == [keys]
    assert TRANSLATIONS_DICT.search(word, count=2, strokes=False) == [word]
    assert TRANSLATIONS_DICT.search(keys, count=None, strokes=True) == [word]
    assert TRANSLATIONS_DICT.search(word, count=None, strokes=False) == [keys]
    assert TRANSLATIONS_DICT.search(re.escape(keys), count=2, strokes=True, regex=True) == [keys]
    assert TRANSLATIONS_DICT.search(re.escape(word), count=2, strokes=False, regex=True) == [word]


INDEX_DICT = StenoIndex(STENO.RSIndexLoad(get_test_filename("index")))
TEST_INDEX = list(INDEX_DICT.items())


@pytest.mark.parametrize("trial", TEST_INDEX)
def test_index_search(trial):
    # Any rule with translations in the index should have its keys and letters somewhere in every entry.
    rname, tdict = trial
    rule = RULES_DICT[rname]
    wresults = INDEX_DICT.search(rname, "", count=100, strokes=False)
    assert all([rule.letters in r for r in wresults])
    kresults = INDEX_DICT.search(rname, "", count=100, strokes=True)
    all_keys = set(rule.keys) - IGNORED_KEYS
    assert all_keys == all_keys.intersection(*kresults)


TEST_RESULTS = [STENO.LXLexerQuery(*t, match_all_keys=True) for t in TEST_TRANSLATIONS]


@pytest.mark.parametrize("result", TEST_RESULTS)
def test_lexer(result):
    """ The parsing tests fail if the parser can't match all the keys. """
    rulemap = result.rulemap
    assert rulemap, f"Lexer failed to match all keys on {result.keys} -> {result.letters}."


@pytest.mark.parametrize("result", TEST_RESULTS)
def test_board(result):
    """ Perform all tests for board diagram output. Currently only checks that the output doesn't raise. """
    STENO.LXBoardFromKeys(result.keys)
    STENO.LXBoardFromRule(result)


@pytest.mark.parametrize("result", TEST_RESULTS)
def test_graph(result):
    """ Perform all tests for text graph output. Mainly limited to examining the node tree for consistency. """
    graph = STENO.LXGraphGenerate(result)
    # The root node uses the top-level rule and has no parent.
    node_index = graph.index._nodes_by_rule
    root = next(iter(node_index))
    assert root.parent is None
    # Every other node descends from it and is unique.
    nodes_list = list(root.descendants())
    nodes_set = set(nodes_list)
    assert len(nodes_list) == len(nodes_set)
    # Going the other direction, every node except the root must have its parent in the set.
    assert all(node.parent in nodes_set for node in nodes_list[1:])
    # The nodes available for interaction must be a subset of our collection.
    assert nodes_set >= set(node_index)


def test_plover():
    """ Make sure the Plover plugin can convert dicts between tuple-based keys and string-based keys. """
    results = []
    engine = PloverEngine.test(TRANSLATIONS_DICT, split_count=3)
    interface = PloverInterface(engine)
    interface.connect(*([results.append] * 2))
    assert results[0] == TRANSLATIONS_DICT
