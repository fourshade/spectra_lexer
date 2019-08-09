from collections import namedtuple

# Contains all static resources necessary for a steno system. The structures are mostly JSON dicts.
# Assets including a key layout, rules, and (optional) board graphics comprise the system.
StenoResources = namedtuple("StenoResources", "layout rules board_defs board_xml")
