""" Unit tests for Plover dictionary conversion. """

from .base import TEST_TRANSLATIONS
from spectra_lexer.plover.plugin import IPlover, PloverExtension, steno_dc_to_dict, StringStenoDict


def test_plover() -> None:
    """ Make sure the Plover plugin can convert dicts between tuple-based keys and string-based keys. """
    assert dc_to_dict(dict_to_dc(TEST_TRANSLATIONS)) == TEST_TRANSLATIONS


def dict_to_dc(translations:StringStenoDict, split_count=3) -> IPlover.StenoDictionaryCollection:
    steno_dc = IPlover.StenoDictionaryCollection()
    dicts = steno_dc.dicts = []
    tuples = [(*k.split("/"),) for k in translations]
    items = list(zip(tuples, translations.values()))
    for i in range(split_count):
        tuple_d = dict(items[i::split_count])
        sd = IPlover.StenoDictionary()
        sd.items = tuple_d.items
        sd.enabled = True
        dicts.append(sd)
    return steno_dc


class DummyEngine:
    compile_dict = staticmethod(steno_dc_to_dict)


def dc_to_dict(steno_dc:IPlover.StenoDictionaryCollection) -> StringStenoDict:
    dummy_engine = DummyEngine()
    ext = PloverExtension(dummy_engine)
    return ext.parse_dictionaries(steno_dc)
