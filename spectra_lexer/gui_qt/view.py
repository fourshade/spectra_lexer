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
        actions = [(self.W_STROKES.toggled,       "VIEWSearch",         ("mode_strokes",)),
                   (self.W_REGEX.toggled,         "VIEWSearch",         ("mode_regex",)),
                   (self.W_INPUT.textEdited,      "VIEWSearch",         ("input_text",)),
                   (self.W_MATCHES.itemSelected,  "VIEWLookup",         ("match_selected",)),
                   (self.W_MAPPINGS.itemSelected, "VIEWQuery",          ("mapping_selected",)),
                   (self.W_BOARD.onActivateLink,  "VIEWSearchExamples"),
                   (self.W_BOARD.onResize,        "VIEWGraphOver",      ("board_aspect_ratio",)),
                   (self.W_TEXT.graphOver,        "VIEWGraphOver",      ("graph_node_ref",)),
                   (self.W_TEXT.graphClick,       "VIEWGraphClick",     ("graph_node_ref",))]
        for signal, *args in actions:
            signal.connect(partial(self.GUIQTAction, *args))
        self.W_BOARD.resizeEvent()
        self._changemap = dict(input_text=self.W_INPUT.setText,
                               matches=self.W_MATCHES.set_items,
                               match_selected=self.W_MATCHES.select,
                               mappings=self.W_MAPPINGS.set_items,
                               mapping_selected=self.W_MAPPINGS.select,
                               link_ref=self.W_BOARD.set_link,
                               board_caption=self.W_DESC.setText,
                               board_xml_data=self.W_BOARD.set_board_data,
                               graph_title=self.W_TITLE.set_text,
                               graph_text=self.W_TEXT.set_interactive_text)
    matches: list = []
    mappings: list = []
    graph_title: str = ""
    graph_text: str = ""
    board_caption: str = ""
    board_xml_data: bytes = b""

    def GUIQTSetEnabled(self, enabled:bool) -> None:
        """ On disable, clear the GUI state and reset all widgets except the title. """
        if not enabled:
            self.W_INPUT.clear()
            self.W_MATCHES.clear()
            self.W_MAPPINGS.clear()
            # old_title = self._state.graph_title
            # self._state = ViewState(graph_title=old_title)
            # self._state.do_updates(self._changemap, update_all=True)

    def GUIQTAction(self, action:str, attrs:tuple=(), *args) -> None:
        self._state.update(zip(attrs, args))
        if action is not None:
            self.VIEWAction(ViewState(self._state, action=action))

    def on_view_finished(self, state:ViewState) -> None:
        state.do_updates(self._changemap)
        self._state.update(state)
