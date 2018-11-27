#!/usr/bin/env python3

""" Main test module for the Spectra steno lexer. Currently handles all components except search and the GUI. """

import pytest

from spectra_lexer.file.base import load_rules_dicts, _RULES_DIR
from spectra_lexer.file.decoder import recursive_decode_all
from spectra_lexer.display.base import OUTPUT_FLAG_SET
from spectra_lexer.display.cascaded_text import CascadedTextDisplay
from spectra_lexer.keys import StenoKeys
from spectra_lexer.lexer import StenoLexer
from spectra_lexer.lexer.match import MATCH_FLAG_SET
from spectra_lexer.rules import KEY_FLAG_SET


def test_dicts():
    """ Load and perform basic integrity tests on the individual rules dictionaries. """
    full_dict = {}
    for d in recursive_decode_all([_RULES_DIR]):
        # Check for rules that have identical names (keys)
        conflicts = set(d).intersection(full_dict)
        assert not conflicts, "Dictionary key {} contained in two or more files".format(conflicts)
        full_dict.update(d)


# Create the minimum necessary components we need for the tests.
RULES_LIST = load_rules_dicts()
LEXER = StenoLexer()
LEXER.engine_connect(None)
LEXER.set_rules(RULES_LIST)
DISPLAY = CascadedTextDisplay()
DISPLAY.engine_connect(None)
LEGAL_FLAGS = MATCH_FLAG_SET | OUTPUT_FLAG_SET | KEY_FLAG_SET


@pytest.mark.parametrize("r", RULES_LIST)
def test_rules(r):
    """ Go through each rule and perform extensive integrity checks. """
    # If the entry has flags, verify that all of them are valid.
    if r.flags:
        bad_flags = set(r.flags) - LEGAL_FLAGS
        assert not bad_flags, "Entry {} has illegal flag(s): {}".format(r.name, bad_flags)
    # A rule with children in a rulemap must conform to strict rules for successful parsing.
    if r.rulemap:
        child_key_sets = [set(cr.keys) for cr in r.rulemap.rules()]
        combined_child_keys = set()
        # Make sure none of the child rules have overlapping keys.
        for s in child_key_sets:
            conflicts = combined_child_keys & s
            assert not conflicts, "Entry {} has child rules with overlapping keys: {}".format(r.name, conflicts)
            combined_child_keys |= s
        # Make sure the child rules contain all the keys of the parent between them (and no extras).
        key_diff = set(r.keys) ^ combined_child_keys
        assert not key_diff, "Entry {} has mismatched keys vs. its child rules: {}".format(r.name, key_diff)


# Test data consisting of a set of steno keys, a word that maps to it, and how many letters that must match.
# A test will fail if an exception is raised or if fewer letters were matched than the goal (which is all by default).
TEST_DATA = [("KW*P",         "Q"),
             ("#T*PBD",       "2nd"),
             ("HAOET",        "heat"),
             ("PHO*PBT",      "month"),
             ("A*BGS",        "action"),
             ("SAOEUT",       "sight"),
             ("PHAER",        "marry"),
             ("SAO*EUT",      "site",        3),
             ("STRAOEUBG",    "strike",      5),
             ("ARPLT",        "apartment",   6),
             ("TPHRABGS",     "interaction", 6),
             ("HRAPB/SKAEUP", "landscape",   7),
             ("RAEURBL/SKUGS/TPA/TAOEG/STKROEPL", "Racial Discussion Fatigue Syndrome", 20)]

MSG_KEYS_FAIL = "Lexer failed to match all keys on {} -> {}."
MSG_LETTERS_FAIL = "Lexer failed to match enough letters on {} -> {}."


@pytest.mark.parametrize("trial", TEST_DATA)
def test_lexer(trial):
    """ Perform all tests for parsing. It fails if the parser can't match all the keys and at least a specified
        number of letters. If no letter count is given, it must match EVERY letter to pass the test."""
    stroke, word, *goals = trial
    keys = StenoKeys.cleanse(stroke)
    if not goals:
        letters_goal = len(word.replace(" ",""))
    else:
        letters_goal = goals[0]
    result = LEXER.query(keys, word)
    rulemap = result.rulemap
    assert rulemap, MSG_KEYS_FAIL.format(stroke, word)
    letters_found = rulemap.letters_matched()
    assert letters_found >= letters_goal, MSG_LETTERS_FAIL.format(stroke, word)


@pytest.mark.parametrize("trial", TEST_DATA)
def test_display(trial):
    """ Produce format for all parsing tests and conduct simple tests. """
    stroke, word, *goal = trial
    keys = StenoKeys.cleanse(stroke)
    result = LEXER.query(keys, word)
    DISPLAY.show_graph(result)
    # Hopefully there is a title and some helper objects after this.
    assert DISPLAY._title
    assert DISPLAY._formatter
    assert DISPLAY._locator
    # The root node starts in the upper left and has no parent.
    root = DISPLAY._root
    assert DISPLAY._locator.get_node_at(0, 0) is root
    assert root.parent is None
    # Every other node descends from it and is unique.
    all_nodes_list = root.get_descendents()
    all_nodes_set = set(all_nodes_list)
    assert len(all_nodes_list) == len(all_nodes_set)
    # Going the other direction, all nodes except the root must have its parent in the set.
    assert all(node is root or node.parent in all_nodes_set for node in all_nodes_list)
    # The nodes available for interaction must be a subset of this collection.
    assert all_nodes_set >= set(DISPLAY._formatter._format_dict)
