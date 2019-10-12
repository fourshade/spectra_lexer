class RuleCaptioner:

    def __init__(self) -> None:
        self._captions = {}

    def add_rule(self, name:str, keys:str, letters:str, desc:str, has_children:bool) -> None:
        """ Generate and add a plaintext caption for a rule. """
        if has_children and letters:
            # Derived rules (i.e. non-leaf nodes) show the complete mapping of keys to letters in their description.
            left_side = f"{keys} → {letters}"
        else:
            # Base rules (i.e. leaf nodes) display their keys to the left of their descriptions.
            left_side = keys
        self._captions[name] = f"{left_side}: {desc}"

    def caption_rule(self, name:str) -> str:
        """ Return the plaintext caption for a rule. """
        return self._captions.get(name, "Unmatched keys")

    @staticmethod
    def caption_lexer(names:list, unmatched_skeys:str) -> str:
        """ Return the caption for a lexer query. """
        if not unmatched_skeys:
            caption = "Found complete match."
        # The output is nowhere near reliable if some keys couldn't be matched.
        elif names:
            caption = "Incomplete match. Not reliable."
        else:
            caption = "No matches found."
        return caption
