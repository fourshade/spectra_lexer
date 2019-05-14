""" Partial class structures that specify a minimum type interface for compatibility with Plover. """

from typing import Callable, Iterable, Optional, Sequence, Tuple

from spectra_lexer.utils import nop

_DEFAULT_TEST_DICT = {"TEFT": "test", "TE*S": "test", "TEFGT": "testing"}

# Key constants and functions for Plover stroke strings.
_PLOVER_SEP = "/"
join_strokes = _PLOVER_SEP.join


class PloverAction:
    prev_attach: bool = True
    text: Optional[str] = "Plover Test"


class PloverTranslation:
    rtfcre: Tuple[str] = ("PHROFR", "TEFT")
    english: Optional[str] = "Plover Test"


class PloverTranslatorState:
    translations: Sequence[PloverTranslation] = [PloverTranslation()]


class PloverStenoDict:
    enabled: bool = True
    items: Callable[[], Iterable[tuple]] = lambda x: []
    __bool__: Callable[[], bool] = lambda x: True


class PloverStenoDictCollection:
    dicts: Iterable[PloverStenoDict] = [PloverStenoDict()]


class PloverEngine:
    dictionaries: PloverStenoDictCollection = PloverStenoDictCollection()
    translator_state: PloverTranslatorState = PloverTranslatorState()
    signal_connect: Callable[[str, Callable], None] = nop
    __enter__: Callable[[], None] = nop
    __exit__: Callable[..., None] = nop

    @classmethod
    def test(cls, d:dict=_DEFAULT_TEST_DICT, split_count:int=1):
        self = cls()
        fd = self.dictionaries = PloverStenoDictCollection()
        fd.dicts = []
        d_list = list(d.items())
        split_list = [dict(d_list[i::split_count]) for i in range(split_count)]
        for split_d in split_list:
            tuple_d = dict(zip(map(tuple, [k.split(_PLOVER_SEP) for k in split_d]), split_d.values()))
            sd = PloverStenoDict()
            sd.items = tuple_d.items
            fd.dicts.append(sd)
        return self
