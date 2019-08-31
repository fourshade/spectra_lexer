""" Minimum type interfaces for compatibility with Plover. """

from typing import Callable, Dict, Iterable, Optional, Sequence, Tuple

# Key constants and functions for Plover stroke strings.
_PLOVER_SEP = "/"
join_strokes = _PLOVER_SEP.join


class dummy:
    """ A robust dummy object. Returns itself through any chain of attribute lookups, subscriptions, and calls. """

    def ret_self(self, *args, **kwargs):
        return self

    __getattr__ = __getitem__ = __call__ = ret_self


class IPloverAction:
    prev_attach: bool = True
    text: Optional[str] = "Plover Test"


class IPloverTranslation:
    rtfcre: Tuple[str, ...] = ("PHROFR", "TEFT")
    english: Optional[str] = "Plover Test"


class IPloverTranslatorState:
    translations: Sequence[IPloverTranslation] = [IPloverTranslation()]


class IPloverStenoDict:
    _dict: Dict[tuple, str] = {}
    def items(self): return self._dict.items()
    enabled: bool = True


class IPloverStenoDictCollection:
    dicts: Iterable[IPloverStenoDict] = [IPloverStenoDict()]


class IPloverEngine:
    dictionaries: IPloverStenoDictCollection = IPloverStenoDictCollection()
    translator_state: IPloverTranslatorState = IPloverTranslatorState()
    signal_connect: Callable[[str, Callable], None] = dummy()
    __enter__: Callable[[], None] = dummy()
    __exit__: Callable[..., None] = dummy()


class FakePloverEngine(IPloverEngine):
    """ Fake Plover engine used for dict conversion testing. """

    def __init__(self, d:dict=None, *, split_count:int=1):
        if d is None:
            d = {"TEFT": "test", "TE*S": "test", "TEFGT": "testing"}
        fd = self.dictionaries = IPloverStenoDictCollection()
        fd.dicts = []
        d_list = list(d.items())
        split_list = [dict(d_list[i::split_count]) for i in range(split_count)]
        for split_d in split_list:
            tuple_d = dict(zip(map(tuple, [k.split(_PLOVER_SEP) for k in split_d]), split_d.values()))
            sd = IPloverStenoDict()
            sd._dict = tuple_d
            fd.dicts.append(sd)
