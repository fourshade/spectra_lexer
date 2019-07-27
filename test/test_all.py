#!/usr/bin/env python3

""" Main test module for the Spectra steno lexer. Currently handles all major components except the GUI. """

from collections import Counter
import os
import re

import pytest

from spectra_lexer.plover.interface import PloverInterface
from spectra_lexer.plover.types import PloverEngine
from spectra_lexer.resource import RuleFlags
from spectra_lexer.resource.resource import ResourceManager
from spectra_lexer.steno.steno import StenoAnalyzer
from spectra_lexer.system.system import SystemManager
from spectra_lexer.types.codec import CSONDict
from spectra_lexer.utils import recurse_attr
from test import get_test_filename

# Create the file handler and use its attributes to update others for loading files.
SYSTEM = SystemManager()
def with_file(cmp):
    cls_attrs = vars(type(cmp))
    for attr in vars(SystemManager):
        if attr not in cls_attrs:
            setattr(cmp, attr, getattr(SYSTEM, attr))
    return cmp
# Load all resources and update components with them as we need them.
RESOURCE = with_file(ResourceManager())
RESOURCE.Load()
def with_rs(cmp):
    for attr in vars(RESOURCE):
        if attr.upper() == attr:
            setattr(cmp, attr, getattr(RESOURCE, attr))
    return cmp


def test_layout():
    """ Test various properties of a key layout for correctness. """
    layout = RESOURCE.LAYOUT
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


RULES_DICT = RESOURCE.RULES


def test_rule_conflicts():
    """ If the size of the dict is less than the sum of its components, some rule names must be identical. """
    pairs = []
    RESOURCE._load(CSONDict, os.path.join(RESOURCE.system_path, "*.cson"), object_pairs_hook=pairs.__iadd__)
    if len(RULES_DICT) < len(pairs):
        keys = next(zip(*pairs))
        conflicts = {k: f"{v} times" for k, v in Counter(keys).items() if v > 1}
        assert not conflicts, f"Found rule keys appearing more than once: {conflicts}"


VALID_FLAGS = set(vars(RuleFlags).values())
IGNORED_KEYS = set("/-")
IGNORED_COUNTER = Counter([*IGNORED_KEYS] * 99)


@pytest.mark.parametrize("r", RULES_DICT.values())
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
        keys -= IGNORED_COUNTER
        assert not keys, f"Entry {r} has mismatched keys vs. its child rules: {list(keys)}"


TRANSLATIONS_DICT = RESOURCE.RSTranslationsLoad(get_test_filename("translations"))
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


INDEX_DICT = RESOURCE.RSIndexLoad(get_test_filename("index"))
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


STENO = with_rs(StenoAnalyzer())
STENO.Load()
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
    nodes_list = list(recurse_attr(root, "children"))
    nodes_set = set(nodes_list)
    assert len(nodes_list) == len(nodes_set)
    # Going the other direction, every node except the root must have its parent in the set.
    assert all(node.parent in nodes_set for node in nodes_list[1:])
    # The nodes available for interaction must be a subset of our collection.
    assert nodes_set >= set(node_index)


PLOVER = PloverInterface()
PLOVER.PLOVER_ENGINE = PloverEngine()


def test_plover():
    """ Make sure the Plover plugin can convert dicts between tuple-based keys and string-based keys. """
    test_engine = PloverEngine.test(TRANSLATIONS_DICT, split_count=3)
    PLOVER.FoundDicts(test_engine.dictionaries)
    assert PLOVER.TRANSLATIONS == TRANSLATIONS_DICT
