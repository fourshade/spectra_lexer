""" Partial class structures that specify a minimum type interface for compatibility with Plover. """

from typing import Callable, Dict, Iterable, Optional, Sequence, Tuple

import pkg_resources

from spectra_lexer.resource import TranslationsDictionary
from spectra_lexer.types import delegate_to
from spectra_lexer.utils import nop

# Key constants and functions for Plover stroke strings.
_PLOVER_SEP = "/"
join_strokes = _PLOVER_SEP.join


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
    __len__ = delegate_to("_dict")
    __iter__ = delegate_to("_dict")
    items = delegate_to("_dict")
    enabled: bool = True


class PloverStenoDictCollection:
    dicts: Iterable[PloverStenoDict] = [PloverStenoDict()]


class PloverEngine:
    dictionaries: PloverStenoDictCollection = PloverStenoDictCollection()
    translator_state: PloverTranslatorState = PloverTranslatorState()
    signal_connect: Callable[[str, Callable], None] = nop
    __enter__: Callable[[], None] = nop
    __exit__: Callable[..., None] = nop

    @classmethod
    def test(cls, d:dict=None, split_count:int=1):
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


class PloverCompatibilityTester:

    _write: Callable[[str], None]  # Error message write callback.

    def __init__(self, write_cb:Callable[[str], None]):
        self._write = write_cb

    def __call__(self, version:str) -> bool:
        """ Check the current Python installation for a compatible version of Plover.
            If the compatibility check fails, send an error message to the callback. """
        try:
            pkg_resources.working_set.require("plover>=" + version)
            return True
        except pkg_resources.ResolutionError:
            self._write(f"ERROR: Plover v{version} or greater required.")
            return False


class PloverTranslationsDictionary(TranslationsDictionary):

    def __init__(self, dicts:Iterable[Dict[tuple, str]]):
        """ Strokes in tuple form must be joined into strings. """
        converted_dict = {}
        for d in dicts:
            converted_dict.update(zip(map(join_strokes, d), d.values()))
        super().__init__(converted_dict)


class TranslationsState:
    """ Keeps running buffers of strokes and text. """

    _BLANK_STATE = ((), "")  # Starting/reset state of translation buffer.

    _strokes: Tuple[str, ...] = ()  # Current sets of contiguous strokes and text.
    _text: str = ""

    def reset(self) -> None:
        self._strokes = ()
        self._text = ""

    def combine(self, new_strokes:Iterable[str], new_text:str) -> None:
        """ Combine all new strokes and text into the current state. """
        self._strokes += new_strokes
        self._text += new_text

    def __iter__(self) -> Iterable[str]:
        """ Yield the joined strokes and current text for lexer queries. """
        yield join_strokes(self._strokes)
        yield self._text
