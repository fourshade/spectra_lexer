""" Module to hold all compatibility-related code for Plover, including partial class typedefs and version check. """

from itertools import chain
from typing import Dict

import pkg_resources

from .types import PloverAction, PloverEngine, PloverStenoDict, PloverStenoDictCollection
from spectra_lexer import Component

# Minimum version of Plover required for plugin compatibility.
_PLOVER_VERSION_REQUIRED = "4.0.0.dev8"
_INCOMPATIBLE_MESSAGE = f"ERROR: Plover v{_PLOVER_VERSION_REQUIRED} or greater required."
# Key constants and functions for Plover stroke strings.
_PLOVER_SEP = "/"
join_strokes = _PLOVER_SEP.join


class PloverCompatibilityLayer(Component):
    """ Component for specific conversions and compatibility checks on Plover's version number and data types. """

    @on("plover_test")
    def test(self) -> None:
        """ Make a fake Plover engine and run some simple tests. """
        self.engine_call("new_plover_engine", self.fake_engine({"TEFT": "test", "TE*S": "test", "TEFGT": "testing"}))
        self.engine_call("plover_new_translation", None, [PloverAction()])

    @on("plover_connect")
    def connect(self, plover_engine:PloverEngine) -> None:
        """ Connect the Plover engine to ours only if a compatible version of Plover is found. """
        if _compatibility_check():
            self.engine_call("new_plover_engine", plover_engine)
        else:
            # If the compatibility check fails, don't try to connect to Plover. Send an error.
            self.engine_call("new_status", _INCOMPATIBLE_MESSAGE)

    @on("plover_convert_dicts", pipe_to="set_dict_translations")
    def convert_dicts(self, steno_dc:PloverStenoDictCollection) -> Dict[str, str]:
        """ When usable Plover dictionaries become available, parse their items into a single string dict.
            Plover dictionaries are not proper Python dicts and cannot be handled as such.
            They only have a subset of the normal dict methods. The fastest of these is d.items(). """
        finished_dict = {}
        for d in steno_dc.dicts:
            if d and d.enabled:
                if isinstance(next(iter(d.items())), tuple):
                    # If strokes are in tuple form, they must be joined into strings.
                    # The fastest method found in profiling uses a chained alternating iterator.
                    kv_alt = chain.from_iterable(d.items())
                    finished_dict.update(zip(map(join_strokes, kv_alt), kv_alt))
                else:
                    finished_dict.update(d.items())
        return finished_dict

    def fake_engine(self, d:dict, split_count:int=1) -> PloverEngine:
        """ Create a fake engine for dictionary parse testing. """
        fake = PloverEngine()
        fake.dictionaries = PloverStenoDictCollection()
        fake.dictionaries.dicts = []
        d_list = list(d.items())
        split_list = [dict(d_list[i::split_count]) for i in range(split_count)]
        for split_d in split_list:
            tuple_d = dict(zip(map(tuple, [k.split(_PLOVER_SEP) for k in split_d]), split_d.values()))
            sd = PloverStenoDict()
            sd.items = tuple_d.items
            fake.dictionaries.dicts.append(sd)
        return fake


def _compatibility_check() -> bool:
    """ Return True only if a compatible version of Plover is found in the working set. """
    try:
        pkg_resources.working_set.require("plover>=" + _PLOVER_VERSION_REQUIRED)
        return True
    except pkg_resources.ResolutionError:
        return False
