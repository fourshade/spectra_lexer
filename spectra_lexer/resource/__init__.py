""" Package with all raw resources necessary to set up a steno system.
    Most structures are parsed from JSON. Built-in assets include a key layout, rules, and board graphics. """

from .board import StenoBoardDefinitions
from .keys import StenoKeyConverter, StenoKeyLayout
from .rules import StenoRule, StenoRuleCollection, StenoRuleParser
from .translations import RTFCREDict, RTFCREExamplesDict
