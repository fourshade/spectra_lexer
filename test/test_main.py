#!/usr/bin/env python3

""" Unit tests for lexical analysis and graphical rendering. """

import pytest

from spectra_lexer import SpectraOptions

from .base import TEST_TRANSLATIONS

SPECTRA = SpectraOptions().compile()
TEST_TRANSLATION_PAIRS = list(TEST_TRANSLATIONS.items())
ALL_KEYS = set().union(*TEST_TRANSLATIONS)
DELIMS = '/-'


def _verify_analysis(analysis) -> None:
    """ An analysis test fails if the output rule is malformed or the lexer can't match all the keys. """
    assert analysis
    analysis.verify(ALL_KEYS, DELIMS)
    for item in analysis:
        assert not item.child.is_unmatched, f"Lexer failed to match all keys on {analysis.keys} -> {analysis.letters}."


@pytest.mark.parametrize("keys, letters", TEST_TRANSLATION_PAIRS)
def test_analysis(keys, letters) -> None:
    """ Perform tests for analysis and output. """
    analysis = SPECTRA.analyzer.query(keys, letters)
    _verify_analysis(analysis)
    # The graph and board tests currently pass as long as they don't raise.
    graph = SPECTRA.graph_engine.graph(analysis)
    for ref, rule in graph.iter_mappings():
        assert graph.draw(ref)
        assert SPECTRA.board_engine.draw_rule(rule)


def test_compound() -> None:
    """ Make sure compound analysis works on full sequences of translations. """
    for i in range(2, len(TEST_TRANSLATION_PAIRS)+1):
        seq = TEST_TRANSLATION_PAIRS[:i]
        compound_rule = SPECTRA.analyzer.compound_query(seq)
        _verify_analysis(compound_rule)
        assert len(list(compound_rule)) == (2 * len(seq) - 1)
