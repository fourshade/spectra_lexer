""" Partial class structures that specify a minimum type interface for compatibility with Plover. """

from typing import Callable, Iterable, Optional, Sequence, Tuple

# Key constants and functions for Plover stroke strings.
_PLOVER_SEP = "/"
join_strokes = _PLOVER_SEP.join
# A robust dummy object. Always returns itself through any chain of attribute lookups, subscriptions, and calls.
_DUMMY_METHODS = ["__getattr__", "__getitem__", "__call__"]
_DUMMY_NAMESPACE = dict.fromkeys(_DUMMY_METHODS, lambda self, *args, **kwargs: self)
dummy = type("dummy", (), _DUMMY_NAMESPACE)()


class PloverAction:
    prev_attach: bool = True
    text: Optional[str] = "Plover Test"


class PloverTranslation:
    rtfcre: Tuple[str, ...] = ("PHROFR", "TEFT")
    english: Optional[str] = "Plover Test"


class PloverTranslatorState:
    translations: Sequence[PloverTranslation] = [PloverTranslation()]


class PloverStenoDict:
    _dict: dict = {}
    def items(self): return self._dict.items()
    enabled: bool = True


class PloverStenoDictCollection:
    dicts: Iterable[PloverStenoDict] = [PloverStenoDict()]


class PloverEngine:
    dictionaries: PloverStenoDictCollection = PloverStenoDictCollection()
    translator_state: PloverTranslatorState = PloverTranslatorState()
    signal_connect: Callable[[str, Callable], None] = dummy
    __enter__: Callable[[], None] = dummy
    __exit__: Callable[..., None] = dummy

    @classmethod
    def test(cls, d:dict=None, *, split_count:int=1):
        if d is None:
            d = {"TEFT": "test", "TE*S": "test", "TEFGT": "testing"}
        self = cls()
        fd = self.dictionaries = PloverStenoDictCollection()
        fd.dicts = []
        d_list = list(d.items())
        split_list = [dict(d_list[i::split_count]) for i in range(split_count)]
        for split_d in split_list:
            tuple_d = dict(zip(map(tuple, [k.split(_PLOVER_SEP) for k in split_d]), split_d.values()))
            sd = PloverStenoDict()
            sd._dict = tuple_d
            fd.dicts.append(sd)
        return self
