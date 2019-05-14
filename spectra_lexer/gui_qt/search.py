from .board import GUIQTBoard
from .window import GUI
from spectra_lexer.core import COREApp, Component
from spectra_lexer.types import delegate_to
from spectra_lexer.view import VIEWSearch


class QtSearch(Component,
               GUI.SearchInput, GUI.SearchMatchList, GUI.SearchMappingList, GUI.SearchToggleStrokes, GUI.SearchToggleRegex,
               COREApp.Start, GUI.Enabled, GUIQTBoard.Link, VIEWSearch.NewInfo, VIEWSearch.Input, VIEWSearch.Matches,
               VIEWSearch.MatchFocus, VIEWSearch.Mappings, VIEWSearch.MappingFocus):
    """ GUI Qt operations class for the left-hand search panel. """

    _state = dict(pattern="",     # Last pattern from user textbox input.
                  match="",       # Last selected match from the upper list.
                  mapping="",     # Last selected match from the upper list.
                  link_name="",   # Name for the most recent rule with examples in the index
                  strokes=False,  # If True, search for strokes instead of translations.
                  regex=False)    # If True, perform search using regex characters.

    def on_app_start(self) -> None:
        """ Connect all Qt signals on GUI load and copy the class state dict to the instance. """
        self._state = self._state.copy()
        self.w_input.textEdited.connect(self._edit_input)
        self.w_matches.itemSelected.connect(self._select_match)
        self.w_mappings.itemSelected.connect(self._select_mapping)
        self.w_strokes.toggled.connect(self._set_mode)
        self.w_regex.toggled.connect(self._set_mode)

    def _send_command(self, command, **updates) -> None:
        """ Send a command with the entire state as keyword args after updating it. """
        self._state.update(updates)
        self.engine_call(command, **self._state)

    def _edit_input(self, pattern:str) -> None:
        self._send_command(VIEWSearch.edit_input, pattern=pattern)

    def _select_match(self, match:str) -> None:
        self._send_command(VIEWSearch.choose_match, match=match)

    def _select_mapping(self, mapping:str) -> None:
        self._send_command(VIEWSearch.choose_mapping, mapping=mapping)

    def on_window_enabled(self, enabled:bool) -> None:
        """ Enable/disable all search widgets. """
        self.w_input.clear()
        self.w_input.setPlaceholderText("Search..." if enabled else "")
        self.w_matches.clear()
        self.w_mappings.clear()
        self.w_input.setEnabled(enabled)
        self.w_matches.setEnabled(enabled)
        self.w_mappings.setEnabled(enabled)
        self.w_strokes.setEnabled(enabled)
        self.w_regex.setEnabled(enabled)

    def _set_mode(self, *dummy) -> None:
        """ When one of the mode checkboxes changes, retry the last search with the new state. """
        self._send_command(VIEWSearch.edit_input, strokes=self.w_strokes.isChecked(), regex=self.w_regex.isChecked())

    def on_view_info(self, caption:str, link_ref:str) -> None:
        self._state.update(link_name=link_ref)

    def on_example_link(self) -> None:
        self._send_command(VIEWSearch.find_examples)

    on_view_search_input = delegate_to("w_input.setText")
    on_view_search_matches = delegate_to("w_matches.set_items")
    on_view_search_match_focus = delegate_to("w_matches.select")
    on_view_search_mappings = delegate_to("w_mappings.set_items")
    on_view_search_mapping_focus = delegate_to("w_mappings.select")
