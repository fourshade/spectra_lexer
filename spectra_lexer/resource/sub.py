""" Module for recursive text substitution algorithms. """

from typing import List, Tuple


class TextSubstitution:
    """ Data structure detailing a substitution in a string of text with the positions where it happened. """

    def __init__(self, ref:str, start:int, length:int) -> None:
        self.ref = ref        # Child pattern reference name.
        self.start = start    # Index of the first character in the parent text where substitution started.
        self.length = length  # Number of characters that were substituted into the parent text.


class TextSubstitutionResult:
    """ Finished text after substitution along with a map of what was done and where. """

    def __init__(self, text:str, subs:Tuple[TextSubstitution]) -> None:
        self.text = text  # Finished text after all substitutions were made.
        self.subs = subs  # Sequence of info structures about the substitutions that were made.


class TextSubstitutionParser:
    """ Performs substitution on text patterns with nested references and returns flattened text and info.
        In order to recursively resolve references, all data should be added before any parsing is done. """

    def __init__(self, *, ref_delims="()", alias_delim="|", allow_duplicates=False) -> None:
        self._ref_delims = ref_delims       # Delimiters marking the start and end of a reference.
        self._alias_delim = alias_delim     # Delimiter between a reference and its alias text when different.
        self._allow_dup = allow_duplicates  # If True, allow references with duplicate names (only the last is kept).
        self._pattern_data = {}             # Dict of input pattern data by reference name.
        self._results = {}                  # Dict of finished substitution results by reference name.

    def add_mapping(self, ref:str, pattern:str) -> None:
        """ Add a mapping for a <ref>erence name to a text <pattern>. The pattern may contain its own references.
            Optionally raise if we try to add references with duplicate names. """
        if not self._allow_dup and ref in self._pattern_data:
            raise ValueError("Duplicate reference name: " + ref)
        self._pattern_data[ref] = pattern

    def parse(self, ref:str) -> TextSubstitutionResult:
        """
        Look up a pattern by reference name and see if we parsed it. If we did, return it immediately.
        Otherwise, find all nested references in brackets and recursively substitute in their text.
        When no alias is given, the referenced text is directly substituted for the bracketed name:

            (.d)e(.s) -> text = 'des', map = ['.d' at 0, '.s' at 2]

        If alias text is included (delimited by '|' by default), that text will be substituted for the name instead:

            (q.)(u|w.) -> letters = 'qu', map = ['q.' at 0, 'w.' at 1]

        Referenced text may contain its own subreferences in brackets, so they must be parsed recursively.
        In the example above, the patterns q. and w. must be parsed before we can finish the 'qu' pattern.
        Circular references are not allowed (and would not make sense anyway).
        """
        if ref in self._results:
            return self._results[ref]
        # Convert the pattern string into a list to allow in-place modification.
        pattern = self._pattern_data[ref]
        p_list = list(pattern)
        subs = []
        lb, rb = self._ref_delims
        # For every bracket match, strip the parentheses to get the reference (and the text for aliases).
        while lb in p_list:
            start = p_list.index(lb)
            end = p_list.index(rb) + 1
            reference = "".join(p_list[start+1:end-1])
            *alias, child_ref = reference.split(self._alias_delim, 1)
            # Look up the child reference. If it is missing, parse its pattern first.
            try:
                text = alias[0] if alias else self.parse(child_ref).text
            except KeyError as e:
                raise KeyError(f"Illegal rule reference {child_ref} in pattern {pattern}") from e
            except ValueError as e:
                raise ValueError(f"Unmatched brackets in rule {child_ref}") from e
            except RecursionError as e:
                raise RecursionError(f"Circular reference descended from rule {child_ref}") from e
            # Add the reference to the info map and substitute the text into the pattern.
            item = TextSubstitution(child_ref, start, len(text))
            subs.append(item)
            p_list[start:end] = text
        result = self._results[ref] = TextSubstitutionResult("".join(p_list), tuple(subs))
        return result

    def inv_parse(self, text:str, child_refs:List[str], child_positions:List[int]) -> str:
        """ Parse text into pattern form by substituting references back in. """
        lb, rb = self._ref_delims
        # Convert the text string into a list to allow in-place modification.
        text = [*text]
        # Replace each reference's text with its parenthesized name. Go from right to left to preserve indexing.
        for name, start in zip(child_refs[::-1], child_positions[::-1]):
            pattern_map = self._results.get(name)
            if pattern_map is not None:
                length = len(pattern_map.letters)
                end = start + length
                text[start:end] = lb, name, rb
        return "".join(text)
