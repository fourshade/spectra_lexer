""" Module to hold all compatibility-related code for Plover, including partial class typedefs and version check. """

from typing import Callable, Iterable, Iterator, Optional, Sequence, Tuple

import pkg_resources

from spectra_lexer.utils import nop

# Minimum version of Plover required for plugin compatibility.
_PLOVER_VERSION_REQUIRED = "4.0.0.dev8"
INCOMPATIBLE_MESSAGE = f"ERROR: Plover v{_PLOVER_VERSION_REQUIRED} or greater required."
# Translations in Plover tuple format for testing the engine.
_TEST_TRANSLATIONS = {("TEFT",): "test", ("TE*S",): "test", ("TEFGT",): "testing"}

# Partial class structures that specify a minimum type interface for compatibility with Plover.
# There are enough default parameters to allow tests by creating a fake engine.
class PloverStenoDict(Iterable):
    enabled: bool = True
    items: Callable[[], Iterator[tuple]] = _TEST_TRANSLATIONS.items
    __iter__: Callable[[], Iterator[tuple]] = _TEST_TRANSLATIONS.__iter__

class PloverStenoDictCollection:
    dicts: Iterable[PloverStenoDict] = [PloverStenoDict()]

class PloverAction:
    prev_attach: bool = True
    text: Optional[str] = "test"

class PloverTranslation:
    rtfcre: Tuple[str] = ("TEFT",)
    english: Optional[str] = "test"

class PloverTranslatorState:
    translations: Sequence[PloverTranslation] = [PloverTranslation()]

class PloverEngine:
    dictionaries: PloverStenoDictCollection = PloverStenoDictCollection()
    translator_state: PloverTranslatorState = PloverTranslatorState()
    __enter__: Callable[[], None] = nop
    __exit__: Callable[..., None] = nop
    signal_connect: Callable[[str, Callable], None] = nop


def compatibility_check() -> bool:
    """ Return True only if a compatible version of Plover is found in the working set. """
    try:
        pkg_resources.working_set.require("plover>=" + _PLOVER_VERSION_REQUIRED)
        return True
    except pkg_resources.ResolutionError:
        return False
