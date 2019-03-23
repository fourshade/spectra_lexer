import re
from collections import Counter
from typing import Dict, Iterable, List, NamedTuple, Sequence, Tuple

from spectra_lexer import Component
from spectra_lexer.steno.keys import StenoKeys
from spectra_lexer.steno.rules import RuleMapItem, StenoRule


# Available bracket pairs for parsing rules.
_LEFT_BRACKETS = r'\(\['
_RIGHT_BRACKETS = r'\)\]'
# Rule substitutions must match a left bracket, one or more non-brackets, and a right bracket.
_SUBRULE_RX = re.compile(r'[{0}][^{0}{1}]+?[{1}]'.format(_LEFT_BRACKETS, _RIGHT_BRACKETS))


class _RawRule(NamedTuple):
    """ Data structure for raw string fields read from each line in a JSON rules file. """
    keys: str                # RTFCRE formatted series of steno strokes.
    pattern: str             # English text pattern, consisting of raw letters as well as references to other rules.
    flag_list: list = ()     # Optional sequence of flags.
    description: str = ""    # Optional description for when the rule is displayed in the GUI.


class RulesManager(Component):
    """ Class which takes a source dict of raw JSON rule entries with nested references and parses
        them recursively to get a final dict of independent steno rules indexed by internal name. """

    files = Resource("cmdline", "rules-files", [":/*.cson"], "Glob patterns for JSON-based rules files to load.")
    out = Resource("cmdline", "rules-out", "./rules.json", "Output file name for lexer-generated rules.")

    _src_dict: Dict[str, _RawRule]   # Keep the source dict in the instance to avoid passing it everywhere.
    _dst_dict: Dict[str, StenoRule]  # Same case for the destination dict. This one needs to be kept as a reference.
    _rev_dict: Dict[StenoRule, str]  # Same case for the reverse reference dict when converting back to JSON form.

    @on("load_dicts", pipe_to="set_dict_rules")
    @on("rules_load", pipe_to="set_dict_rules")
    def load(self, filenames:Sequence[str]=()) -> Dict[str, StenoRule]:
        """ Top level loading method. Goes through source JSON dicts and parses every entry using mutual recursion. """
        # Load rules from each source dictionary and convert to namedtuple form.
        dicts = self.engine_call("file_load_all", *(filenames or self.files))
        self._src_dict = {k: _RawRule(*v) for d in dicts for (k, v) in d.items()}
        # If the size of the combined dict is less than the sum of its components, some rule names are identical.
        if len(self._src_dict) < sum(map(len, dicts)):
            conflicts = {k: f"{v} files" for k, v in Counter(sum(map(list, dicts), [])).items() if v > 1}
            raise KeyError(f"Found rule keys appearing in more than one file: {conflicts}")
        # Parse all rules from the source dictionary into the final one, indexed by name.
        # This will parse entries in a semi-arbitrary order, so make sure not to redo any.
        d = self._dst_dict = {}
        try:
            for k in self._src_dict:
                if k not in d:
                    self._parse(k)
        except KeyError as e:
            raise KeyError(f"Illegal reference descended from rule {k}") from e
        # The final dict must be reversed one-to-one to look up names given rules. Some components need this.
        self._rev_dict = {v: k for (k, v) in d.items()}
        self.engine_call("set_dict_rules_reversed", self._rev_dict)
        # Return the final rules dict. Components such as the lexer may throw away the names.
        return d

    def _parse(self, k:str) -> None:
        """ Parse a source dictionary rule into a StenoRule object and store it. """
        raw = self._src_dict[k]
        # We have to substitute in the effects of all child rules. These determine the final letters and rulemap.
        letters, built_map = self._substitute(raw.pattern)
        # The keys must be converted from RTFCRE form into lexer form.
        keys = StenoKeys.from_rtfcre(raw.keys)
        # The flags and built rulemap must be frozen before final inclusion in an immutable rule.
        self._dst_dict[k] = StenoRule(keys, letters, frozenset(raw.flag_list), raw.description, tuple(built_map))

    def _substitute(self, pattern:str) -> Tuple[str, List[RuleMapItem]]:
        """
        From a rule's raw pattern string, find all the child rule references in brackets and make a map
        so the format code can break it down again if needed. For those in () brackets, we must substitute
        in the letters: (.d)e(.s) -> des. For [] brackets, the letters and reference are given separately.

        Only already-finished rules from the results dict can be directly substituted. Any rules that are
        not finished yet will still contain their own child rules in brackets. If we find one of these,
        we have to parse it first in a recursive manner. Circular references will crash the program.
        """
        built_map = []
        m = _SUBRULE_RX.search(pattern)
        while m:
            # For every child rule, strip the parentheses to get the dict key (and the letters for [] rules).
            rule_str = m.group()
            if rule_str[0] == '(':
                letters = None
                rule_key = rule_str[1:-1]
            else:
                (letters, rule_key) = rule_str[1:-1].split("|", 1)
            # Look up the child rule and parse it if it hasn't been yet. Even if we aren't using its letters,
            # we still need to parse it at this stage so that the correct reference goes in the rulemap.
            if rule_key not in self._dst_dict:
                self._parse(rule_key)
            rule = self._dst_dict[rule_key]
            # Add the rule to the map and substitute in the letters if necessary.
            if not letters:
                letters = rule.letters
            built_map.append(RuleMapItem(rule, m.start(), len(letters)))
            pattern = pattern.replace(rule_str, letters)
            m = _SUBRULE_RX.search(pattern)
        return pattern, built_map

    @on("rules_save", pipe_to="file_save")
    def save(self, rules:Iterable[StenoRule], filename:str="") -> tuple:
        """ From a bare iterable of rules (generally from the lexer), make a new raw dict and save it to JSON
            using auto-generated reference names and substituting rules in each rulemap for their letters. """
        return (filename or self.out), {str(r): self._inv_parse(r) for r in rules}

    def _inv_parse(self, r:StenoRule) -> _RawRule:
        """ Convert a StenoRule object into a raw series of fields. """
        # The keys must be converted to RTFCRE form.
        keys = r.keys.rtfcre
        # The pattern must be deduced from the letters, the rulemap, and the reference dict.
        pattern = self._inv_substitute(r.letters, r.rulemap)
        # Put the flags into a list. The description is copied verbatim.
        return _RawRule(keys, pattern, list(r.flags), r.desc)

    def _inv_substitute(self, letters:str, rulemap:Sequence[RuleMapItem]) -> str:
        """ For each mapped rule with a name reference, replace the mapped letters with the reference. """
        # Go from right to left to preserve indexing.
        for item in reversed(rulemap):
            r = item.rule
            # Some rules aren't named or are special. Don't show these in the pattern.
            name = self._rev_dict.get(r)
            if not name:
                continue
            # Some rules take up no letters. Don't add these even if references exist.
            start = item.start
            end = start + item.length
            if start == end:
                continue
            # Replace the letters this rule takes up with a standard parenthesized reference.
            letters = letters[:start] + f"({name})" + letters[end:]
        return letters
