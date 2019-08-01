from traceback import TracebackException
from typing import Iterable

from PyQt5.QtWidgets import QLabel, QLineEdit, QCheckBox

from .base import GUIQT
from .widgets import MainMenu, MainWindow, SearchListWidget, StenoBoardWidget, TextGraphWidget, TextTitleWidget
from spectra_lexer.core import CORE
from spectra_lexer.view import VIEW


class GUIUpdater(dict):
    """ Mapping with GUI methods to call when a particular part of the state changes. """

    def __call__(self, attrs:dict) -> None:
        """ For every attribute given, call the corresponding GUI method if one exists. """
        for k in attrs:
            if k in self:
                self[k](attrs[k])


class QtViewManager(CORE, VIEW, GUIQT):
    """ The main GUI Qt operations class. Controls all main view panels. """

    window: MainWindow = None  # Main GUI window. All GUI activity is coupled to this window.
    w_menu: MainMenu = None
    w_board: StenoBoardWidget = None
    w_desc: QLabel = None
    w_title: TextTitleWidget = None
    w_text: TextGraphWidget = None
    w_input: QLineEdit = None
    w_matches: SearchListWidget = None
    w_mappings: SearchListWidget = None
    w_strokes: QCheckBox = None
    w_regex: QCheckBox = None

    _last_status: str = ""
    _state_vars: dict = None        # Contains a complete representation of the current state of the GUI.
    _update_gui: GUIUpdater = None  # Call with a dict to update the actual GUI widgets.

    def Load(self) -> None:
        """ Create the window and connect all GUI controls to its widgets.
            Connect all Qt signals and initialize the board size.
            Display the last status if it occurred before connection. """
        window = MainWindow()
        widgets = window.widgets()
        for k, v in widgets.items():
            setattr(self, k, v)
        self._state_vars = {}
        self._update_gui = self._output_updater()
        for signal, action, *attrs in self._input_actions():
            def run(*values, _action=action, _attrs=attrs) -> None:
                """ Update the state (but not the GUI), then run the action. """
                self._state_vars.update(zip(_attrs, values))
                self.GUIQTAction(_action)
            signal.connect(run)
        if self._last_status:
            self.w_title.set_text(self._last_status)
        self.window.show()
        self.set_enabled(True)

    def _input_actions(self) -> Iterable[tuple]:
        """ Return all possible user input signals and the corresponding actions with any state updates. """
        return [(self.w_strokes.toggled,       "VIEWSearch",     "mode_strokes"),
                (self.w_regex.toggled,         "VIEWSearch",     "mode_regex"),
                (self.w_input.textEdited,      "VIEWSearch",     "input_text"),
                (self.w_matches.itemSelected,  "VIEWLookup",     "match_selected"),
                (self.w_mappings.itemSelected, "VIEWSelect",     "mapping_selected"),
                (self.w_title.textEdited,      "VIEWQuery",      "translation"),
                (self.w_text.graphOver,        "VIEWGraphOver",  "graph_node_ref"),
                (self.w_text.graphClick,       "VIEWGraphClick", "graph_node_ref"),
                (self.w_board.onActivateLink,  "VIEWSearchExamples"),
                (self.w_board.onResize,        "VIEWGraphOver",  "board_aspect_ratio")]

    def _output_updater(self) -> GUIUpdater:
        """ Return a dict with all possible GUI methods to call when a particular part of the state changes. """
        return GUIUpdater(input_text=self.w_input.setText,
                          matches=self.w_matches.set_items,
                          match_selected=self.w_matches.select,
                          mappings=self.w_mappings.set_items,
                          mapping_selected=self.w_mappings.select,
                          translation=self.w_title.set_text,
                          graph_text=self.w_text.set_interactive_text,
                          board_caption=self.w_desc.setText,
                          board_xml_data=self.w_board.set_board_data,
                          link_ref=self.w_board.set_link)

    def set_enabled(self, enabled:bool) -> None:
        """ Enable/disable all widgets when GUI-blocking operations are being done. """
        if not enabled:
            # On disable, reset all widgets except the title.
            self.GUIQTAction("VIEWReset")
        self.w_menu.setEnabled(enabled)
        self.w_input.setEnabled(enabled)
        self.w_input.setPlaceholderText("Search..." if enabled else "")
        self.w_matches.setEnabled(enabled)
        self.w_mappings.setEnabled(enabled)
        self.w_strokes.setEnabled(enabled)
        self.w_regex.setEnabled(enabled)
        self.w_board.resizeEvent()

    def GUIQTShowWindow(self) -> None:
        self.window.show()

    def GUIQTCloseWindow(self) -> None:
        self.window.close()

    def GUIQTUpdate(self, **kwargs) -> None:
        """ For every attribute given, update our state dict and the GUI widgets. """
        self._state_vars.update(kwargs)
        self._update_gui(kwargs)

    def GUIQTAction(self, action:str, **override) -> None:
        self.VIEWAction({**self._state_vars, **override}, action)

    def VIEWActionResult(self, changed:dict) -> None:
        """ After any action, run through the changes and update the state and widgets with any relevant ones. """
        self.GUIQTUpdate(**changed)

    def COREStatus(self, status:str) -> None:
        """ Show engine status messages in the title as well. Save the last one if we're not connected yet. """
        try:
            self.w_title.set_text(status)
        except Exception:
            self._last_status = status

    def COREException(self, exc:Exception, max_frames:int=10) -> bool:
        """ Print an exception traceback to the main text widget, if possible. """
        try:
            tb = TracebackException.from_exception(exc, limit=max_frames)
            tb_text = "".join(tb.format())
            self.w_title.set_text("Well, this is embarrassing...", dynamic=False)
            self.w_text.set_plaintext(tb_text)
        except Exception:
            # The Qt GUI is probably what raised the error in the first place.
            # Re-raising will kill the program. Let lower-level handlers try first.
            pass
        return True
