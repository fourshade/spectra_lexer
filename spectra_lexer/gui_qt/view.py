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
        self._connect(self.W_STROKES.toggled, "VIEWSearch", "mode_strokes")
        self._connect(self.W_REGEX.toggled, "VIEWSearch", "mode_regex")
        self._connect(self.W_INPUT.textEdited, "VIEWSearch", "input_text")
        self._connect(self.W_MATCHES.itemSelected, "VIEWLookup", "match_selected")
        self._connect(self.W_MAPPINGS.itemSelected, "VIEWQuery", "mapping_selected")
        self._connect(self.W_BOARD.onActivateLink, "VIEWSearchExamples")
        self.W_BOARD.onResize.connect(self._on_resize)
        self.W_TEXT.textMouseAction.connect(self._graph_action)
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

    def _connect(self, signal, action:str, *attrs) -> None:
        """ Send a command with a copy of the entire state after updating attributes. """
        def call(*args):
            self._state.update(zip(attrs, args), action=action)
            self._execute()
        signal.connect(call)

    def _on_resize(self, ratio:float) -> None:
        self._state.board_aspect_ratio = ratio

    def _graph_action(self, row:int, col:int, clicked:bool) -> None:
        self._state.graph_location = [row, col]
        self._state.action = "VIEWGraphClick" if clicked else "VIEWGraphOver"
        self._execute()

    def on_view_finished(self, state:ViewState) -> None:
        state.do_updates(self._changemap)
        self._state.update(state)

    def _execute(self) -> None:
        self.VIEWAction(ViewState(self._state))
