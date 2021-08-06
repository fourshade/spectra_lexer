""" Module for recursive text substitution algorithms. """

from typing import Sequence


class TextSubstitution:
    """ Data structure detailing a substitution in a string of text with the positions where it happened. """

    def __init__(self, ref:str, start:int, length:int) -> None:
        self.ref = ref        # Child pattern reference name.
        self.start = start    # Index of the first character in the parent text where substitution started.
        self.length = length  # Number of characters that were substituted into the parent text.


class TextSubstitutionResult:
    """ Finished text after substitution along with a map of what was done and where. """

    def __init__(self, text:str, subs:Sequence[TextSubstitution]) -> None:
        self.text = text  # Finished text after all substitutions were made.
        self.subs = subs  # Sequence of info structures about the substitutions that were made.


class TextSubstitutionParser:
    """ Performs substitution on text patterns with nested references and returns flattened text and info.
        In order to recursively resolve references, all data should be added before any parsing is done. """

    def __init__(self, ref_start="(", ref_end=")", escape="\\", alias_delim="|", *, allow_duplicates=False) -> None:
        assert len(ref_start) == 1
        assert len(ref_end) == 1
        assert len(escape) == 1
        self._ref_start = ref_start         # Delimiter marking the start of a reference.
        self._ref_end = ref_end             # Delimiter marking the end of a reference.
        self._escape = escape               # Escape character for <ref_start> as a literal.
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
        char_list = list(pattern)
        subs = []
        start = 0
        # Find every pair of parentheses and parse the references.
        while True:
            try:
                start = char_list.index(self._ref_start, start)
            except ValueError:
                break
            # If an escape precedes a ref start, remove the escape and continue.
            if start > 0 and char_list[start - 1] == self._escape:
                del char_list[start - 1]
                continue
            end = char_list.index(self._ref_end, start) + 1
            reference = "".join(char_list[start+1:end-1])
            if self._alias_delim in reference:
                # Aliases include the text substitution directly in the pattern itself.
                # The reference still goes in the table, but no lookup is done.
                text, reference = reference.split(self._alias_delim, 1)
            else:
                # Look up the reference and its text substitution. If missing, parse it first.
                try:
                    text = self.parse(reference).text
                except KeyError as e:
                    raise KeyError(f"Illegal rule reference {reference} in pattern {pattern}") from e
                except ValueError as e:
                    raise ValueError(f"Unmatched brackets in rule {reference}") from e
                except RecursionError as e:
                    raise RecursionError(f"Circular reference descended from rule {reference}") from e
            # Add the reference to the info map and substitute the text into the pattern.
            item = TextSubstitution(reference, start, len(text))
            subs.append(item)
            char_list[start:end] = text
        full_text = "".join(char_list)
        result = self._results[ref] = TextSubstitutionResult(full_text, subs)
        return result
