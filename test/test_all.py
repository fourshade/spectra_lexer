#!/usr/bin/env python3

""" Main test module for the Spectra steno lexer. Currently handles all major components except the GUI. """

from collections import Counter
import os
import re

import pytest

from spectra_lexer.plover.interface import PloverInterface
from spectra_lexer.steno.board import BoardRenderer
from spectra_lexer.steno.graph import GraphRenderer
from spectra_lexer.steno.index import IndexManager
from spectra_lexer.steno.lexer import StenoLexer
from spectra_lexer.steno.rules import RuleFlags
from spectra_lexer.steno.search import SearchEngine
from spectra_lexer.steno.system import SystemManager
from spectra_lexer.steno.translations import TranslationsManager
from spectra_lexer.system.file import SYSFile, FileHandler
from spectra_lexer.types.codec import CSONDict
from test import get_test_filename

# Create the file handler and make a fake engine call method just to load files.
FILE = FileHandler()
FILE.asset_path = FILE.user_path = "spectra_lexer"
def file_call(key, *args, call_table={v: getattr(FILE, k) for k, v in vars(SYSFile).items()}, **kwargs):
    if key in call_table:
        return call_table[key](*args, **kwargs)


# Create components and load resources for the tests in order as we need them.
SYSTEM = SystemManager()
SYSTEM.engine_call = file_call
SYSTEM_LAYOUT, SYSTEM_RULES, SYSTEM_BOARD = SYSTEM.load()


def test_layout():
    """ Test various properties of a key layout for correctness. """
    layout = SYSTEM_LAYOUT
    # There cannot be duplicate keys within a side.
    sides = [layout.LEFT, layout.CENTER, layout.RIGHT]
    left, center, right = sets = list(map(set, sides))
    assert sum(map(len, sets)) == sum(map(len, sides))
    # The center keys must not share any characters with the sides.
    assert center.isdisjoint(left)
    assert center.isdisjoint(right)
    # The left and right sides must not share characters after casing.
    assert left.isdisjoint(map(str.lower, right))
    # The divider keys must not duplicate normal keys.
    all_keys = left | center | right
    assert layout.SEP not in all_keys
    assert layout.SPLIT not in all_keys
    # Shift keys as well as all transform values must be valid keys previously defined.
    for shift_key, shift_transform in layout.SHIFT_TABLE.items():
        assert {shift_key, *shift_transform.values()} <= all_keys


def test_rule_conflicts():
    """ If the size of the full dict is less than the sum of its components, some rule names must be identical. """
    dicts = [CSONDict.decode(p) for p in FILE.read_all([os.path.join(SYSTEM.path, SYSTEM.RULES_PATH)])]
    if len(SYSTEM_RULES) < sum(map(len, dicts)):
        conflicts = {k: f"{v} files" for k, v in Counter(sum(map(list, dicts), [])).items() if v > 1}
        assert not conflicts, f"Found rule keys appearing in more than one file: {conflicts}"


VALID_FLAGS = set(vars(RuleFlags).values())
IGNORED_KEYS = Counter({"/": 999, "-": 999})


@pytest.mark.parametrize("r", SYSTEM_RULES.values())
def test_rules(r):
    """ Go through each rule and perform extensive integrity checks. """
    # If the entry has flags, verify that all of them are valid.
    if r.flags:
        bad_flags = r.flags - VALID_FLAGS
        assert not bad_flags, f"Entry {r} has illegal flag(s): {bad_flags}"
    # Make sure the child rules contain all the keys of the parent between them, and no extras.
    if r.rulemap:
        keys = Counter(r.keys)
        keys.subtract(Counter([k for cr in r.rulemap for k in cr.rule.keys]))
        keys -= IGNORED_KEYS
        assert not keys, f"Entry {r} has mismatched keys vs. its child rules: {list(keys)}"


TRANSLATIONS = TranslationsManager()
TRANSLATIONS.engine_call = file_call
TRANSLATIONS_DICT = TRANSLATIONS.load(get_test_filename("translations"))
TEST_TRANSLATIONS = list(TRANSLATIONS_DICT.items())
LEXER = StenoLexer()
LEXER.layout = SYSTEM_LAYOUT
LEXER.rules = SYSTEM_RULES
LEXER.on_app_start()
TEST_RESULTS = [LEXER.query(*t, need_all_keys=True) for t in TEST_TRANSLATIONS]


@pytest.mark.parametrize("result", TEST_RESULTS)
def test_lexer(result):
    """ The parsing tests fail if the parser can't match all the keys. """
    rulemap = result.rulemap
    assert rulemap, f"Lexer failed to match all keys on {result.keys} -> {result.letters}."


INDEX = IndexManager()
INDEX.engine_call = file_call
INDEX_DICT = INDEX.load(get_test_filename("index"))
TEST_INDEX = list(INDEX_DICT.items())
SEARCH = SearchEngine()
SEARCH.rules = SYSTEM_RULES
SEARCH.translations = TRANSLATIONS_DICT
SEARCH.index = INDEX_DICT


@pytest.mark.parametrize("trial", TEST_TRANSLATIONS)
def test_search(trial):
    """ Go through each loaded test translation and check the search engine in all modes. """
    keys, word = trial
    # For both keys and word, and in either mode, search should return a list with only the item itself.
    assert SEARCH.search(word, strokes=False) == [word]
    assert SEARCH.search(keys, strokes=True) == [keys]
    assert SEARCH.search(re.escape(keys), strokes=True, regex=True) == [keys]
    assert SEARCH.search(re.escape(word), strokes=False, regex=True) == [word]


# def test_rules_search():
#     """ A rules prefix search with no body should return every rule we have after expanding it all we can. """
#     results = SEARCH.search("/")
#     while "(more...)" in results:
#         SEARCH._add_page_to_count()
#         results = SEARCH._repeat_search()
#     assert len(results) == len(RULES_DICT)


@pytest.mark.parametrize("trial", TEST_INDEX)
def test_index_search(trial):
    # Any rule with translations in the index should have its keys and letters somewhere in every entry.
    rname, tdict = trial
    rule = SYSTEM_RULES[rname]
    wresults = SEARCH.search(f"//{rname}", strokes=False)
    assert all([rule.letters in r for r in wresults])
    kresults = SEARCH.search(f"//{rname}", strokes=True)
    all_keys = set(rule.keys) - set("/-")
    assert all_keys == all_keys.intersection(*kresults)


BOARD = BoardRenderer()
BOARD.engine_call = file_call
BOARD.layout = SYSTEM_LAYOUT
BOARD.rules = SYSTEM_RULES
BOARD.board = SYSTEM_BOARD
BOARD.on_app_start()


@pytest.mark.parametrize("result", TEST_RESULTS)
def test_board(result):
    """ Perform all tests for board diagram output. Currently only checks that the output doesn't raise. """
    BOARD.from_keys(result.keys)
    BOARD.from_rule(result)


GRAPH = GraphRenderer()
GRAPH.layout = SYSTEM_LAYOUT


@pytest.mark.parametrize("result", TEST_RESULTS)
def test_graph(result):
    """ Perform all tests for text graph output. Mainly limited to examining the node tree for consistency. """
    graph = GRAPH._make_graph(result, True, True)
    # The root node uses the top-level rule and has no parent.
    root = graph.from_rule(result)
    assert root.parent is None
    # Every other node descends from it and is unique.
    nodes_list = list(root.descendents())
    nodes_set = set(nodes_list)
    assert len(nodes_list) == len(nodes_set)
    # Going the other direction, all nodes except the root must have its parent in the set.
    assert all(node.parent in nodes_set for node in nodes_list[1:])
    # The nodes available for interaction must be a subset of our collection.
    assert nodes_set >= set(graph._formatter._ref_dict)


PLOVER = PloverInterface()


def test_plover():
    """ Make sure the Plover interface can convert dicts between tuple-based keys and string-based keys. """
    test_dc = PLOVER.test(TRANSLATIONS_DICT, split_count=3).dictionaries
    assert len(PLOVER._convert_dicts(test_dc)) == len(TRANSLATIONS_DICT)
