from functools import partial
from typing import Callable, Iterable

from .base import GUIQT
from spectra_lexer.view import ViewState


class QtViewController:
    """ Holds the current GUI state and dispatches calls to the view layer. """

    _RESET_STATE: dict = vars(ViewState)  # Contains all default values necessary to reset the GUI.

    _state: dict           # Contains a complete representation of the current state of the GUI.
    _run_action: Callable  # Call with an action and prepared state for the view layer.
    _update_gui: Callable  # Call with a dict to update the actual GUI widgets.

    def __init__(self, runner:Callable, updater:Callable):
        self._state = {}
        self._run_action = runner
        self._update_gui = updater

    def __call__(self, action, attrs:Iterable[str]=(), *values, **cfg_override) -> None:
        """ Update the state WITHOUT calling any GUI methods (because the user did it), then run the action. """
        d = self._state
        if attrs:
            d.update(zip(attrs, values))
        self._run_action(action, ViewState(d), **cfg_override)

    def update(self, d:dict) -> None:
        """ For every attribute given, update our state dict and the GUI widgets. """
        self._state.update(d)
        self._update_gui(d)

    def reset(self) -> None:
        """ Clear the GUI widgets and state. """
        self._state = {}
        self._update_gui(self._RESET_STATE)

    def apply_changes(self, state:ViewState) -> None:
        """ After any action, run through the changes and update the state and widgets with any relevant ones. """
        self.update(state.changed())


class GUIUpdater(dict):
    """ Mapping with GUI methods to call when a particular part of the state changes. """

    def __call__(self, attrs:dict) -> None:
        """ For every attribute given, call the corresponding GUI method if one exists. """
        for k in attrs:
            if k in self:
                self[k](attrs[k])


class QtView(GUIQT):
    """ GUI Qt operations class for the main view panels. """

    _controller: QtViewController = None

    def GUIQTConnect(self) -> None:
        """ Connect all Qt signals and initialize the board size. """
        self._controller = QtViewController(self.VIEWAction, self._output_updater())
        for signal, action, *attrs in self._input_actions():
            signal.connect(partial(self._controller, action, attrs))
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
            old_title = self.W_TITLE.text()
            self._controller.reset()
            self.W_TITLE.set_text(old_title)

    def GUIQTUpdate(self, **kwargs) -> None:
        self._controller.update(kwargs)

    def GUIQTAction(self, action:str, **cfg_override) -> None:
        self._controller(action, **cfg_override)

    def VIEWActionResult(self, *args) -> None:
        self._controller.apply_changes(*args)
