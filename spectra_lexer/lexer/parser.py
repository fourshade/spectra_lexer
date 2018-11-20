import re
from typing import Dict, Iterable, Tuple

from spectra_lexer.file import RawRulesDictionary
from spectra_lexer.keys import StenoKeys
from spectra_lexer.rules import RuleMap, StenoRule

# Available bracket pairs for parsing rules and the regex pattern that uses them.
LEFT_BRACKETS = r'\(\['
RIGHT_BRACKETS = r'\)\]'
SUBRULE_RX = re.compile(r'[{0}][^{0}{1}]*?[{1}]'.format(LEFT_BRACKETS, RIGHT_BRACKETS))


class StenoRuleParser(Dict[str, StenoRule]):
    """ Class which gets a freshly loaded source dict of raw JSON entries and parses them
        recursively to get a final set of independent steno rules indexed by internal name.
        That this class subclasses dict is an implementation detail only. """

    _src_dict: RawRulesDictionary  # Keep the source dict in the instance to avoid passing it everywhere.

    def __init__(self, src_dict:RawRulesDictionary):
        """ Top level parsing method. Goes through source JSON dict and parses every entry using mutual recursion. """
        # Unpack rules from all source dictionaries in the given filename list or directory (built-in by default).
        self._src_dict = src_dict
        # Parse all rules from source dictionary into this one, indexed by name.
        # This will parse entries in a semi-arbitrary order, so make sure not to redo any.
        super().__init__()
        for k in self._src_dict.keys():
            if k not in self:
                self._parse(k)

    def __iter__(self) -> Iterable[StenoRule]:
        """ Return only the parsed rules one-by-one. This should be the only public accessor. """
        return iter(self.values())

    def _parse(self, k:str) -> None:
        """ Parse a source dictionary rule into a StenoRule object. """
        raw_rule = self._src_dict[k]
        # The keys must be converted from RTFCRE form into lexer form.
        keys = StenoKeys.parse(raw_rule.keys)
        # We have to substitute in the effects of all child rules. These determine the final letters and rulemap.
        letters, rulemap = self._substitute(raw_rule.pattern)
        # Look for key flags, add them as ending rules, and remove them.
        flags = set(raw_rule.flag_str.split("|")) if raw_rule.flag_str else set()
        if flags:
            rulemap.add_key_rules(flags, len(letters), remove_flags=True)
        description = raw_rule.description
        # For now, just include examples as a line after the description joined with commas.
        if raw_rule.example_str:
            description = "{}\n({})".format(description, raw_rule.example_str.replace("|", ", "))
        self[k] = StenoRule(k, keys, letters, flags, description, rulemap)

    def _substitute(self, pattern:str) -> Tuple[str, RuleMap]:
        """
        From a rule's raw YAML pattern string, find all the child rule references in brackets and make a map
        so the format code can break it down again if needed. For those in () brackets, we must substitute
        in their letters as well: (.d)e(.s) -> des. For [] brackets, only add the rulemap entries.

        Only already-finished rules from the results dict can be directly substituted. Any rules that are
        not finished yet will still contain their own child rules in brackets. If we find one of these,
        we have to parse it first in a recursive manner. Circular references will crash the program.
        """
        rulemap = RuleMap()
        m = SUBRULE_RX.search(pattern)
        while m:
            # For every child rule, strip the parentheses to get the dict key (and the letters for () rules).
            rule_str = m.group()
            if rule_str[0] == '(':
                letters = None
                rule_key = rule_str[1:-1]
            else:
                (letters, rule_key) = rule_str[1:-1].split("|", 1)
            # Look up the child rule and parse it if it hasn't been yet. Even if we aren't using its letters,
            # we still need to parse it at this stage so that the correct reference goes in the rulemap.
            if rule_key not in self:
                if rule_key not in self._src_dict:
                    raise KeyError("Illegal reference: {} in {}".format(rule_key, pattern))
                self._parse(rule_key)
            rule = self[rule_key]
            # Add the rule to the map and substitute in the letters if necessary.
            if not letters:
                letters = rule.letters
            rulemap.add_child(rule, m.start(), len(letters))
            pattern = pattern.replace(rule_str, letters)
            m = SUBRULE_RX.search(pattern)
        return pattern, rulemap
