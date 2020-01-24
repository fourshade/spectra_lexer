#!/usr/bin/env python3

""" Unit tests for Plover dictionary conversion. """

from typing import Dict

from .base import TEST_TRANSLATIONS
from spectra_lexer.plover import IPlover, PloverExtension


def test_plover() -> None:
    """ Make sure the Plover plugin can convert dicts between tuple-based keys and string-based keys. """
    assert dc_to_dict(dict_to_dc(TEST_TRANSLATIONS)) == TEST_TRANSLATIONS


def dict_to_dc(translations:Dict[str, str], split_count=3) -> IPlover.StenoDictCollection:
    steno_dc = IPlover.StenoDictCollection()
    dicts = steno_dc.dicts = []
    tuples = [(*k.split("/"),) for k in translations]
    items = list(zip(tuples, translations.values()))
    for i in range(split_count):
        tuple_d = dict(items[i::split_count])
        sd = IPlover.StenoDict()
        sd.items = tuple_d.items
        sd.enabled = True
        dicts.append(sd)
    return steno_dc


class DummyEngine(IPlover.Engine):
    signal_connect = __enter__ = __exit__ = lambda *_: False


def dc_to_dict(steno_dc:IPlover.StenoDictCollection) -> Dict[str, str]:
    dummy_engine = DummyEngine()
    dummy_engine.dictionaries = steno_dc
    ext = PloverExtension(dummy_engine)
    return ext.parse_dictionaries()
