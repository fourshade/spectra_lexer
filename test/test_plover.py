#!/usr/bin/env python3

""" Unit tests for Plover dictionary conversion. """

from typing import Dict

from .base import TEST_TRANSLATIONS
from spectra_lexer.gui_qt.plover import IPloverStenoDictCollection, IPloverStenoDict, \
    PloverEngineWrapper, PloverTranslationParser


def test_plover() -> None:
    """ Make sure the Plover plugin can convert dicts between tuple-based keys and string-based keys. """
    assert dc_to_dict(dict_to_dc(TEST_TRANSLATIONS)) == TEST_TRANSLATIONS


def dict_to_dc(translations:Dict[str, str], split_count=3) -> IPloverStenoDictCollection:
    steno_dc = IPloverStenoDictCollection()
    dicts = steno_dc.dicts = []
    tuples = [(*k.split("/"),) for k in translations]
    items = list(zip(tuples, translations.values()))
    for i in range(split_count):
        tuple_d = dict(items[i::split_count])
        sd = IPloverStenoDict()
        sd.items = tuple_d.items
        sd.enabled = True
        dicts.append(sd)
    return steno_dc


def dc_to_dict(steno_dc:IPloverStenoDictCollection) -> Dict[str, str]:
    wrapper = PloverEngineWrapper()
    parser = PloverTranslationParser()
    d = wrapper.compile_raw_dict(steno_dc)
    return parser.convert_dict(d)
