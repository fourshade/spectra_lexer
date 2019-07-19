from typing import Iterable

from .base import GUIQT


class GUIUpdater(dict):
    """ Mapping with GUI methods to call when a particular part of the state changes. """

    def __call__(self, attrs:dict) -> None:
        """ For every attribute given, call the corresponding GUI method if one exists. """
        for k in attrs:
            if k in self:
                self[k](attrs[k])


class QtView(GUIQT):
    """ GUI Qt operations class for the main view panels. """

    _state_vars: dict = None        # Contains a complete representation of the current state of the GUI.
    _update_gui: GUIUpdater = None  # Call with a dict to update the actual GUI widgets.

    def GUIQTConnect(self) -> None:
        """ Connect all Qt signals and initialize the board size. """
        self._state_vars = {}
        self._update_gui = self._output_updater()
        for signal, action, *attrs in self._input_actions():
            def run(*values, _action=action, _attrs=attrs) -> None:
                """ Update the state (but not the GUI), then run the action. """
                self._state_vars.update(zip(_attrs, values))
                self.GUIQTAction(_action)
            signal.connect(run)
        self.W_BOARD.resizeEvent()

    def _input_actions(self) -> Iterable[tuple]:
        """ Return all possible user input signals and the corresponding actions with any state updates. """
        return [(self.W_STROKES.toggled,       "VIEWSearch",     "mode_strokes"),
                (self.W_REGEX.toggled,         "VIEWSearch",     "mode_regex"),
                (self.W_INPUT.textEdited,      "VIEWSearch",     "input_text"),
                (self.W_MATCHES.itemSelected,  "VIEWLookup",     "match_selected"),
                (self.W_MAPPINGS.itemSelected, "VIEWSelect",     "mapping_selected"),
                (self.W_TITLE.textEdited,      "VIEWQuery",      "translation"),
                (self.W_TEXT.graphOver,        "VIEWGraphOver",  "graph_node_ref"),
                (self.W_TEXT.graphClick,       "VIEWGraphClick", "graph_node_ref"),
                (self.W_BOARD.onActivateLink,  "VIEWSearchExamples"),
                (self.W_BOARD.onResize,        "VIEWGraphOver",  "board_aspect_ratio")]

    def _output_updater(self) -> GUIUpdater:
        """ Return a dict with all possible GUI methods to call when a particular part of the state changes. """
        return GUIUpdater(input_text=self.W_INPUT.setText,
                          matches=self.W_MATCHES.set_items,
                          match_selected=self.W_MATCHES.select,
                          mappings=self.W_MAPPINGS.set_items,
                          mapping_selected=self.W_MAPPINGS.select,
                          translation=self.W_TITLE.set_text,
                          graph_text=self.W_TEXT.set_interactive_text,
                          board_caption=self.W_DESC.setText,
                          board_xml_data=self.W_BOARD.set_board_data,
                          link_ref=self.W_BOARD.set_link)

    def GUIQTSetEnabled(self, enabled:bool) -> None:
        """ On disable, reset all widgets except the title. """
        if not enabled:
            self.GUIQTAction("VIEWReset")

    def GUIQTUpdate(self, **kwargs) -> None:
        """ For every attribute given, update our state dict and the GUI widgets. """
        self._state_vars.update(kwargs)
        self._update_gui(kwargs)

    def GUIQTAction(self, action:str, **override) -> None:
        self.VIEWAction({**self._state_vars, **override}, action)

    def VIEWActionResult(self, changed:dict) -> None:
        """ After any action, run through the changes and update the state and widgets with any relevant ones. """
        self.GUIQTUpdate(**changed)
