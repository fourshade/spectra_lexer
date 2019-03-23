""" Partial class structures that specify a minimum type interface for compatibility with Plover. """

from typing import Callable, Iterable, Optional, Sequence, Tuple

from spectra_lexer.utils import nop


class PloverStenoDict:
    enabled: bool = True
    items: Callable[[], Iterable[tuple]] = lambda x: []
    __bool__: Callable[[], bool] = lambda x: True


class PloverStenoDictCollection:
    dicts: Iterable[PloverStenoDict] = [PloverStenoDict()]


class PloverAction:
    prev_attach: bool = True
    text: Optional[str] = "Plover Test"


class PloverTranslation:
    rtfcre: Tuple[str] = ("PHROFR", "TEFT")
    english: Optional[str] = "Plover Test"


class PloverTranslatorState:
    translations: Sequence[PloverTranslation] = [PloverTranslation()]


class PloverEngine:
    dictionaries: PloverStenoDictCollection = PloverStenoDictCollection()
    translator_state: PloverTranslatorState = PloverTranslatorState()
    signal_connect: Callable[[str, Callable], None] = nop
    __enter__: Callable[[], None] = nop
    __exit__: Callable[..., None] = nop
