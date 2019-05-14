from typing import List

from .base import GUIQT


class QtSearch(GUIQT):
    """ GUI Qt operations class for the left-hand search panel. """

    _state = dict(pattern="",     # Last pattern from user textbox input.
                  match="",       # Last selected match from the upper list.
                  mapping="",     # Last selected match from the upper list.
                  link_name="",   # Name for the most recent rule with examples in the index
                  strokes=False,  # If True, search for strokes instead of translations.
                  regex=False)    # If True, perform search using regex characters.

    def GUIQTConnect(self) -> None:
        """ Connect all Qt signals on GUI load and copy the class state dict to the instance. """
        self._state = self._state.copy()
        self.W_INPUT.textEdited.connect(self._edit_input)
        self.W_MATCHES.itemSelected.connect(self._select_match)
        self.W_MAPPINGS.itemSelected.connect(self._select_mapping)
        self.W_STROKES.toggled.connect(self._set_mode)
        self.W_REGEX.toggled.connect(self._set_mode)
        self.W_BOARD.onActivateLink.connect(self._click_example_link)

    def _send_command(self, command, **updates) -> None:
        """ Send a command with the entire state as keyword args after updating it. """
        self._state.update(updates)
        command(**self._state)

    def _edit_input(self, pattern:str) -> None:
        self._send_command(self.search_edit_input, pattern=pattern)

    def _select_match(self, match:str) -> None:
        self._send_command(self.search_choose_match, match=match)

    def _select_mapping(self, mapping:str) -> None:
        self._send_command(self.search_choose_mapping, mapping=mapping)

    def _click_example_link(self) -> None:
        self._send_command(self.search_find_examples)

    def _set_mode(self, *dummy) -> None:
        """ When one of the mode checkboxes changes, retry the last search with the new state. """
        self._send_command(self.search_edit_input, strokes=self.W_STROKES.isChecked(), regex=self.W_REGEX.isChecked())

    def VIEWSetInput(self, text:str) -> None:
        self.W_INPUT.setText(text)
        self._state.update(pattern=text)

    def VIEWSetMatches(self, str_list:List[str], selection:str=None) -> None:
        self.W_MATCHES.set_items(str_list)
        if selection is not None:
            self.W_MATCHES.select(selection)
            self._state.update(match=selection)

    def VIEWSetMappings(self, str_list:List[str], selection:str=None) -> None:
        self.W_MAPPINGS.set_items(str_list)
        if selection is not None:
            self.W_MAPPINGS.select(selection)
            self._state.update(mapping=selection)

    def VIEWSetLink(self, link_ref:str) -> None:
        """ Show a link in the bottom-right corner and save the reference. """
        self._state.update(link_name=link_ref)
        self.W_BOARD.set_link(link_ref)
