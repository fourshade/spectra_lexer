from functools import partial

from .base import GUIQT
from spectra_lexer.view import ViewState, VIEW


class _GUIQT_VIEW(GUIQT):

    @VIEW.VIEWAction.response
    def on_view_finished(self, state:ViewState) -> None:
        """ After any action, run through the changes and update the GUI with any relevant ones. """
        raise NotImplementedError


class QtView(_GUIQT_VIEW):
    """ GUI Qt operations class for the main view panels. """

    _state: ViewState = ViewState()  # Contains a complete representation of the state of the GUI.
    _changemap: dict = {}            # Mapping of state attributes to GUI methods that reflect their changes.

    def GUIQTConnect(self) -> None:
        """ Connect all Qt signals on GUI load and initialize the board size.
            When a mode checkbox changes, retry the last search with the new state. """
        self._state = ViewState()
        actions = [(self.W_STROKES.toggled,       "VIEWSearch",         "mode_strokes"),
                   (self.W_REGEX.toggled,         "VIEWSearch",         "mode_regex"),
                   (self.W_INPUT.textEdited,      "VIEWSearch",         "input_text"),
                   (self.W_MATCHES.itemSelected,  "VIEWLookup",         "match_selected"),
                   (self.W_MAPPINGS.itemSelected, "VIEWQuery",          "mapping_selected"),
                   (self.W_BOARD.onActivateLink,  "VIEWSearchExamples", None),
                   (self.W_BOARD.onResize,        "VIEWGraphOver",      "board_aspect_ratio"),
                   (self.W_TEXT.graphOver,        "VIEWGraphOver",      "graph_node_ref"),
                   (self.W_TEXT.graphClick,       "VIEWGraphClick",     "graph_node_ref")]
        for signal, action, attr in actions:
            signal.connect(partial(self._call, action, attr))
        self.W_BOARD.resizeEvent()
        self._changemap = dict(input_text=self.W_INPUT.setText,
                               matches=self.W_MATCHES.set_items,
                               match_selected=self.W_MATCHES.select,
                               mappings=self.W_MAPPINGS.set_items,
                               mapping_selected=self.W_MAPPINGS.select,
                               link_ref=self.W_BOARD.set_link,
                               board_caption=self.W_DESC.setText,
                               board_xml_data=self.W_BOARD.set_board,
                               graph_title=self.W_TITLE.set_text,
                               graph_text=self.W_TEXT.set_interactive_text)

    def _call(self, action:str, attr:str, *args) -> None:
        """ Update an attribute and/or send an action command with a copy of the entire state. """
        if attr is not None:
            self._state[attr], = args
        if action is not None:
            self.VIEWAction(ViewState(self._state, action=action))

    def on_view_finished(self, state:ViewState) -> None:
        state.do_updates(self._changemap)
        self._state.update(state)
