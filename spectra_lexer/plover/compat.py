from typing import Callable, Iterable, Iterator, Optional, Sequence

import pkg_resources

# Minimum version of Plover required for plugin compatibility.
_PLOVER_VERSION_REQUIRED = "4.0.0.dev8"
INCOMPATIBLE_MESSAGE = "ERROR: Plover v{} or greater required.".format(_PLOVER_VERSION_REQUIRED)

# Partial class structures that specify a minimum level of functionality for compatibility with Plover.
class PloverStenoDict(Iterable):
    enabled: bool
    items: Callable[[], Iterator[tuple]]

class PloverStenoDictCollection:
    dicts: Iterable[PloverStenoDict]

class PloverAction:
    prev_attach: bool
    text: Optional[str]

class PloverTranslation:
    rtfcre: tuple
    english: Optional[str]

class PloverTranslatorState:
    translations: Sequence[PloverTranslation]

class PloverEngine:
    dictionaries: PloverStenoDictCollection
    translator_state: PloverTranslatorState
    signal_connect: Callable[[str, Callable], None]


def compatibility_check() -> bool:
    """ Return True only if a compatible version of Plover is found in the working set. """
    try:
        pkg_resources.working_set.require("plover>=" + _PLOVER_VERSION_REQUIRED)
        return True
    except pkg_resources.ResolutionError:
        return False
